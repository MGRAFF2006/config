#!/usr/bin/env python3
"""Install face-first polkit PAM and a camera-only helper sandbox exception."""

import argparse
import configparser
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HOWDY_CONFIG = Path("/etc/howdy/config.ini")
PAM_TARGET = Path("/etc/pam.d/polkit-1")
DROPIN_TARGET = Path("/etc/systemd/system/polkit-agent-helper@.service.d/howdy-camera.conf")
VENDOR_UNIT = Path("/usr/lib/systemd/system/polkit-agent-helper@.service")
SYSTEM_AUTH = Path("/etc/pam.d/system-auth")
# A face match is "sufficient" and skips system-auth's whole auth section. These
# are the only auth modules that may be skipped: password methods, lockout
# bookkeeping (preauth runs first in the managed stack) and environment setup.
SKIPPABLE_AUTH = {"pam_faillock.so", "pam_systemd_home.so", "pam_unix.so", "pam_permit.so", "pam_env.so"}


def camera_path(config=HOWDY_CONFIG):
    parser = configparser.ConfigParser()
    with config.open() as stream:
        parser.read_file(stream)
    path = parser.get("video", "device_path")
    # Keep unit specifiers, quoting and list syntax out of this generated rule.
    # Colons are normal in stable PCI camera aliases and are escaped separately.
    if not re.fullmatch(r"/dev/[A-Za-z0-9_./:+-]+", path) or ".." in Path(path).parts:
        raise ValueError("Howdy device_path must be a literal path below /dev")
    return path


def check_system_auth(path=SYSTEM_AUTH):
    """Refuse when face success would skip an auth guard this stack does not know."""
    unknown = []
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0].startswith("@"):  # @include pulls in unchecked lines
            unknown.append(line.strip())
            continue
        if fields[0].lstrip("-") != "auth":
            continue
        rest = line.split(None, 1)[1].strip() if len(fields) > 1 else ""
        if rest.startswith("[") and "]" in rest:
            control, module = "[...]", rest.split("]", 1)[1].split()[:1]
        else:
            control, module = (rest.split() + [""])[0], rest.split()[1:2]
        name = Path(module[0]).name if module else ""
        if control in ("include", "substack") or name not in SKIPPABLE_AUTH:
            unknown.append(line.strip())
    if unknown:
        raise ValueError(f"{path} has auth steps a face match would skip: " + "; ".join(unknown))


def render_dropin(camera):
    # BindPaths parses colon-separated tuples. DeviceAllow does not.
    escaped = camera.replace(":", r"\x3a")
    template = (ROOT / "system/polkit/howdy-camera.conf").read_text()
    return template.replace("@BIND_CAMERA@", escaped).replace("@CAMERA@", camera).encode()


def plan(config=HOWDY_CONFIG):
    camera = camera_path(config)
    return camera, {
        PAM_TARGET: (ROOT / "system/pam.d/polkit-1").read_bytes(),
        DROPIN_TARGET: render_dropin(camera),
    }


def verify_unit(dropin):
    with tempfile.TemporaryDirectory(prefix="howdy-polkit-unit-") as directory:
        unit = Path(directory) / VENDOR_UNIT.name
        unit.write_bytes(VENDOR_UNIT.read_bytes() + b"\n" + dropin)
        result = subprocess.run(["systemd-analyze", "verify", str(unit)], capture_output=True, text=True)
        if result.returncode or result.stderr.strip():
            raise ValueError("Generated helper unit did not validate: " + result.stderr.strip())


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def install_files(files, backup, reload_manager):
    changed = {path: content for path, content in files.items()
               if path.is_symlink() or not path.is_file() or path.read_bytes() != content
               or stat.S_IMODE(path.stat().st_mode) != 0o644 or path.stat().st_uid != os.geteuid()}
    if not changed:
        return False
    backup.mkdir(parents=True, mode=0o700)
    originals = {}
    for path in changed:
        if path.exists() or path.is_symlink():
            saved = backup / path.relative_to("/")
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved, follow_symlinks=False)
            originals[path] = saved
        else:
            originals[path] = None
    try:
        for path, content in changed.items():
            atomic_write(path, content)
        reload_manager()
    except BaseException:
        for path, saved in originals.items():
            if saved is None:
                path.unlink(missing_ok=True)
            else:
                fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".restore-", dir=path.parent)
                os.close(fd)
                restored = Path(temporary)
                restored.unlink()
                try:
                    shutil.copy2(saved, restored, follow_symlinks=False)
                    os.replace(restored, path)
                finally:
                    restored.unlink(missing_ok=True)
        # The first reload may have partially succeeded. Restore the old view.
        try:
            reload_manager()
        except subprocess.CalledProcessError:
            pass
        raise
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    camera, files = plan()
    verify_unit(files[DROPIN_TARGET])
    try:
        check_system_auth()
    except ValueError as error:
        parser.error(str(error))
    if args.check:
        failures = [str(path) for path, content in files.items()
                    if path.is_symlink() or not path.is_file() or path.read_bytes() != content
                    or stat.S_IMODE(path.stat().st_mode) != 0o644 or path.stat().st_uid != 0]
        if failures:
            raise SystemExit("Drift: " + ", ".join(failures))
        print("PASS: face-first polkit PAM and camera-only helper exception match")
        return
    if not args.apply:
        print("Camera: " + camera)
        for path, content in files.items():
            print(str(path) + ":\n" + content.decode())
        print("Use --apply as root. This reloads systemd only; it restarts no desktop or display manager.")
        return
    if os.geteuid() != 0:
        parser.error("--apply requires root")
    camera_stat = Path(camera).stat()
    if not stat.S_ISCHR(camera_stat.st_mode):
        parser.error("Howdy's configured camera is not a character device")
    subsystem = Path(f"/sys/dev/char/{os.major(camera_stat.st_rdev)}:{os.minor(camera_stat.st_rdev)}/subsystem")
    if subsystem.resolve().name != "video4linux":
        parser.error("Howdy's configured device is not a Video4Linux capture device")
    if not Path("/usr/lib/security/pam_howdy.so").is_file():
        parser.error("pam_howdy.so is missing")
    backup = Path("/var/backups/config-howdy-polkit") / datetime.now().astimezone().strftime("%Y-%m-%d-%H%M%S-%f")
    changed = install_files(files, backup, lambda: subprocess.run(["systemctl", "daemon-reload"], check=True))
    print("Installed; backup: " + str(backup) if changed else "Already installed; no changes")


if __name__ == "__main__":
    main()
