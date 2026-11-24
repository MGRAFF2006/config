#!/usr/bin/env python3
"""Install password-first polkit PAM with an explicit face option and its helper sandbox exception."""

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
FAILLOCK_CONF = Path("/etc/security/faillock.conf")
DEFAULT_TALLY_DIR = "/run/faillock"
# Programs and modules the managed stack runs inside the helper sandbox.
REQUIRED_FILES = ("/usr/bin/grep", "/usr/lib/security/pam_exec.so", "/usr/lib/security/pam_faillock.so",
                  "/usr/lib/security/pam_howdy.so")
# The face path never runs system-auth's auth section. These are the only auth
# modules it may skip: password methods, lockout bookkeeping (the face path runs
# its own preauth first) and environment setup.
SKIPPABLE_AUTH = {"pam_faillock.so", "pam_systemd_home.so", "pam_unix.so", "pam_permit.so", "pam_env.so"}
# The face path's guard is plain "pam_faillock.so preauth", which reads
# FAILLOCK_CONF. system-auth must use that same policy: only the action and
# logging words may appear, never conf=, dir=, deny= or other policy options.
FAILLOCK_PLAIN_ARGS = {"preauth", "authfail", "authsucc", "silent", "audit", "no_log_info"}


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


def check_workaround(config=HOWDY_CONFIG):
    """The password gate leaves the (possibly empty) answer in PAM_AUTHTOK.
    Howdy's input/native workarounds read it and would skip the face attempt."""
    parser = configparser.ConfigParser()
    with config.open() as stream:
        parser.read_file(stream)
    if parser.get("core", "workaround", fallback="input").strip() != "off":
        raise ValueError(f"{config}: set [core] workaround = off for the polkit face option")


def check_system_auth(path=SYSTEM_AUTH):
    """Refuse when the face path would skip an auth guard or use another lockout policy."""
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
            control, words = "[...]", rest.split("]", 1)[1].split()
        else:
            control, words = (rest.split() + [""])[0], rest.split()[1:]
        name = Path(words[0]).name if words else ""
        if control in ("include", "substack") or name not in SKIPPABLE_AUTH:
            unknown.append(line.strip())
        elif name == "pam_faillock.so" and not set(words[1:]) <= FAILLOCK_PLAIN_ARGS:
            unknown.append(line.strip() + " (custom pam_faillock options)")
    if unknown:
        raise ValueError(f"{path} has auth steps the face path would skip or not match: " + "; ".join(unknown))


def tally_dir(conf=FAILLOCK_CONF):
    """Return the faillock tally directory that FAILLOCK_CONF selects."""
    directory = DEFAULT_TALLY_DIR
    for line in conf.read_text().splitlines():
        if line.strip().startswith("#"):
            continue
        name, _, value = line.partition("=")
        if name.strip() == "dir":
            directory = value.strip()
    # Literal path for ReadWritePaths=; never the root or a top-level directory.
    if (not re.fullmatch(r"/[A-Za-z0-9_./+-]+", directory) or ".." in Path(directory).parts
            or len(Path(directory).parts) < 3):
        raise ValueError(f"{conf}: unsupported faillock dir {directory!r}")
    return str(Path(directory))


def render_dropin(camera, tally):
    # BindPaths parses colon-separated tuples. DeviceAllow does not.
    escaped = camera.replace(":", r"\x3a")
    template = (ROOT / "system/polkit/howdy-camera.conf").read_text()
    return (template.replace("@BIND_CAMERA@", escaped).replace("@CAMERA@", camera)
            .replace("@TALLY_DIR@", tally).encode())


def plan(config=HOWDY_CONFIG, faillock_conf=FAILLOCK_CONF, system_auth=SYSTEM_AUTH):
    camera = camera_path(config)
    check_workaround(config)
    check_system_auth(system_auth)
    return camera, {
        PAM_TARGET: (ROOT / "system/pam.d/polkit-1").read_bytes(),
        DROPIN_TARGET: render_dropin(camera, tally_dir(faillock_conf)),
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
    try:
        camera, files = plan()
    except (OSError, ValueError, configparser.Error) as error:
        parser.error(str(error))
    verify_unit(files[DROPIN_TARGET])
    if args.check:
        failures = [str(path) for path, content in files.items()
                    if path.is_symlink() or not path.is_file() or path.read_bytes() != content
                    or stat.S_IMODE(path.stat().st_mode) != 0o644 or path.stat().st_uid != 0]
        if failures:
            raise SystemExit("Drift: " + ", ".join(failures))
        print("PASS: password-first polkit PAM and the helper camera/tally exception match")
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
    missing = [path for path in REQUIRED_FILES if not Path(path).is_file()]
    if missing:
        parser.error("missing: " + ", ".join(missing))
    backup = Path("/var/backups/config-howdy-polkit") / datetime.now().astimezone().strftime("%Y-%m-%d-%H%M%S-%f")
    changed = install_files(files, backup, lambda: subprocess.run(["systemctl", "daemon-reload"], check=True))
    print("Installed; backup: " + str(backup) if changed else "Already installed; no changes")


if __name__ == "__main__":
    main()
