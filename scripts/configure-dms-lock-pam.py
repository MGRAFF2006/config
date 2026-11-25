#!/usr/bin/env python3
"""Point DMS at the managed greeter/lock PAM stacks.

Usage: configure-dms-lock-pam.py [--check] CONFIG_HOME
CONFIG_HOME is the user's XDG config directory (usually ~/.config). DMS 2.1
reads CONFIG_HOME/dms/settings.json; ~/.config/DankMaterialShell is a legacy
path that DMS no longer reads, so it is never edited here.

Before any change, every input that could give DMS a security-key setting is
read: settings.json, every file in CONFIG_HOME/dms/config.d, the packaged and
administrator cli-policy.json, DMS_POLICY_LOCK_SETTINGS in this environment,
and the launch environment of the user's running DMS/Quickshell processes.
The PAM stacks involved are read too: the lock stack DMS uses now
(lockPamPath, or login when it is empty), the greetd and dankshell stacks this
replaces, and every file they include. A security-key module in any of them
also refuses, since the managed stacks have none.
The check does not reproduce how DMS merges them. It refuses when any of them,
at any level and in any letter case, has a security-key setting that is not
clearly off, so it can refuse more often than DMS would require a key, but it
never lets the migration drop one.
--check only runs that check and never writes.
Exit status: 0 done (or would be); 2 refused because of a security-key setting;
3 the settings file does not exist yet (2 and 3 change nothing); 1 an error:
an input could not be read or parsed (nothing changed), or the write failed,
and the message says whether settings.json was changed.
"""

import json
import math
import os
import re
from pathlib import Path
import sys
import tempfile

MANAGED_LOCK = "/etc/pam.d/dankshell"
EXTERNAL_FLAGS = ("greeterPamExternallyManaged", "lockPamExternallyManaged")
# DMS 2.1.2 core/internal/clipolicy: the only policy files it reads.
POLICY_PATHS = (Path("/usr/share/dms/cli-policy.json"), Path("/etc/dms/cli-policy.json"))
POLICY_ENV = "DMS_POLICY_LOCK_SETTINGS"
# `dms run` starts the shell as qs/quickshell with POLICY_ENV in its environment.
PROC = Path("/proc")
# The security-key settings of DMS 2.1.2 (Common/settings/SettingsSpec.js and
# Common/SettingsData.qml) and the only values that leave each clearly off.
# None (JSON null) never turns one on. Any other value, including 0, "" for a
# switch or "OR", counts as possibly on.
# PAM modules for security keys and smartcards; the managed stacks use none.
SECURITY_KEY_MODULES = ("pam_u2f", "pam_yubico", "pam_p11", "pam_pkcs11")
PAM_DIRS = (Path("/etc/pam.d"), Path("/usr/lib/pam.d"))
REPLACED_STACKS = ("greetd", "dankshell")
PAM_INCLUDE = re.compile(r"^(?:@include\s+(\S+)|-?\w+\s+(?:include|substack)\s+(\S+))", re.IGNORECASE)
SECURITY_KEY_OFF = {
    "enableU2f": (False,),
    "u2fMode": ("or",),
    "greeterEnableU2f": (False,),
    "lockPamInlineU2f": (False,),
    "lockU2fPamPath": ("",),
}


class SettingsError(Exception):
    pass


def reject_constant(name):
    raise ValueError(f"{name} is not JSON")


def finite_float(text):
    # Python reads 1e400 as inf and would write it back as Infinity, which is not JSON.
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"number {text} is out of range")
    return value


def reject_duplicates(pairs):
    keys = [key for key, _ in pairs]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise ValueError(f"duplicate key {duplicates[0]!r}")
    return dict(pairs)


def parse_strict(label, raw):
    """Strict JSON: valid UTF-8 without a BOM, no NaN/Infinity, no duplicate
    keys. An empty or blank file holds no settings."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SettingsError(f"{label} is not valid UTF-8: {error}") from error
    if not text.strip():
        return {}
    try:
        return json.loads(text, parse_constant=reject_constant, parse_float=finite_float,
                          object_pairs_hook=reject_duplicates)
    except (ValueError, RecursionError) as error:
        raise SettingsError(f"cannot parse {label}: {error}") from error


def read_file(path):
    if not path.is_file():
        raise SettingsError(f"{path} is not a regular file")
    try:
        return parse_strict(str(path), path.read_bytes())
    except OSError as error:
        raise SettingsError(f"cannot read {path}: {error}") from error


def overlay_inputs(directory):
    """Every entry of config.d except subdirectories: hidden files and any name
    count, whether or not DMS would load them."""
    if not directory.is_dir():
        return []
    try:
        entries = sorted(directory.iterdir())
    except OSError as error:
        raise SettingsError(f"cannot list {directory}: {error}") from error
    return [(str(entry), read_file(entry)) for entry in entries if not entry.is_dir()]


def policy_inputs():
    return [(str(path), read_file(path)) for path in POLICY_PATHS if path.exists()]


def dms_process_name(pid_dir):
    """The process name if it looks like DMS or Quickshell (comm or argv[0]), else None."""
    argv0 = (pid_dir / "cmdline").read_bytes().split(b"\0")[0]
    names = ((pid_dir / "comm").read_text(errors="replace").strip(),
             os.path.basename(argv0.decode(errors="replace")))
    return next((name for name in names if name in ("qs", "dms") or "quickshell" in name.lower()), None)


def process_uids(pid_dir):
    for line in (pid_dir / "status").read_text().splitlines():
        if line.startswith("Uid:"):
            return {int(field) for field in line.split()[1:]}
    return set()


def environment_inputs(uids):
    """POLICY_ENV here and in the launch environment of each running DMS or
    Quickshell process of the target user. A shell keeps the value it was
    started with, whatever the policy files say now."""
    inputs = []
    value = os.environb.get(POLICY_ENV.encode())
    if value is not None:
        inputs.append((f"${POLICY_ENV}", parse_strict(f"${POLICY_ENV}", value)))
    for pid_dir in sorted(PROC.iterdir(), key=lambda entry: entry.name):
        if not pid_dir.name.isdigit():
            continue
        try:
            name = process_uids(pid_dir) & uids and dms_process_name(pid_dir)
            if not name:
                continue
            environment = (pid_dir / "environ").read_bytes()
        except (FileNotFoundError, ProcessLookupError):
            continue  # exited meanwhile
        except OSError as error:
            raise SettingsError(f"cannot inspect running process {pid_dir.name}, which may be DMS: "
                                f"{error}") from error
        label = f"${POLICY_ENV} of running {name} (pid {pid_dir.name})"
        for entry in environment.split(b"\0"):
            if entry.startswith(POLICY_ENV.encode() + b"="):
                inputs.append((label, parse_strict(label, entry.split(b"=", 1)[1])))
    return inputs


def pam_file(name):
    """The file PAM reads for a service or include name, or None."""
    if name.startswith("/"):
        return Path(name) if Path(name).is_file() else None
    return next((directory / name for directory in PAM_DIRS if (directory / name).is_file()), None)


def security_key_modules(settings):
    """Lines loading a security-key module in the lock stack DMS uses now, the
    stacks this replaces, and every file they include."""
    lock = settings.get("lockPamPath") if isinstance(settings, dict) else None
    pending = [lock if isinstance(lock, str) and lock else "login", *REPLACED_STACKS]
    seen, found = set(), []
    while pending:
        path = pam_file(pending.pop())
        if path is None or path in seen:
            continue
        seen.add(path)
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError as error:
            raise SettingsError(f"cannot read PAM file {path}: {error}") from error
        for number, line in enumerate(lines, 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            included = PAM_INCLUDE.match(line)
            if included:
                pending.append(included.group(1) or included.group(2))
            if any(module in line.lower() for module in SECURITY_KEY_MODULES):
                found.append(f"{path}:{number}: {line}")
    return found


def target_uids(config_home):
    """The user whose DMS this configures: the owner of CONFIG_HOME and the
    invoking user (the sudo caller when run through sudo)."""
    uids = {int(os.environ.get("SUDO_UID", os.getuid())) if os.getuid() == 0 else os.getuid()}
    if config_home.exists():
        uids.add(config_home.stat().st_uid)
    return uids


def keys_anywhere(value):
    """Every (key, value) pair at any nesting level."""
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                yield key, child
                pending.append(child)
        elif isinstance(item, list):
            pending.extend(item)


def clearly_off(value, off_values):
    return value is None or any(type(value) is type(off) and value == off for off in off_values)


def security_key_settings(inputs):
    off_values = {name.casefold(): off for name, off in SECURITY_KEY_OFF.items()}
    found = []
    for label, value in inputs:
        for key, setting in keys_anywhere(value):
            off = off_values.get(key.casefold())
            if off is not None and not clearly_off(setting, off):
                found.append(f"{label}: {key} = {json.dumps(setting)}")
    return found


def refuse(path, found, settings):
    print(f"[ERROR] DMS may require a security key, which the managed lock would drop. "
          "These security-key settings are not clearly off:", file=sys.stderr)
    for line in found:
        print(f"[ERROR]   {line}", file=sys.stderr)
    print(f"[ERROR] The managed lock sets lockPamExternallyManaged=true in {path}, which makes "
          f"DMS skip its own security-key step, and {MANAGED_LOCK} has no pam_u2f. This check "
          "does not work out how DMS combines its settings; it refuses on any of these "
          "settings anywhere: off means enableU2f, greeterEnableU2f and lockPamInlineU2f "
          'false, u2fMode "or" and lockU2fPamPath empty. Nothing was changed.', file=sys.stderr)
    if isinstance(settings, dict) and settings.get("lockPamExternallyManaged") is True:
        print("[ERROR] lockPamExternallyManaged is already true, so DMS may be skipping "
              "the key now; set it to false to restore the key.", file=sys.stderr)
    print("[ERROR] To use the managed password/face lock, remove these settings or set them "
          "off, restart DMS if a running process is listed, then re-run.", file=sys.stderr)
    return 2


class WriteError(Exception):
    def __init__(self, error, replaced):
        super().__init__(str(error))
        self.replaced = replaced


def write_atomically(path, data, original):
    """Replace the file as DMS itself saves it (QSaveFile): a temporary file in the
    same directory, flushed to disk, then renamed over it. Mode and owner are
    kept; a symlink keeps pointing at it. If the file no longer holds
    `original` (DMS saved meanwhile), nothing is replaced. DMS does not lock
    the file, so a save between that comparison and the rename can still be
    overwritten; the comparison only narrows that window to the rename itself.
    WriteError.replaced says whether the rename happened, i.e. whether the new
    settings are in place."""
    target = Path(os.path.realpath(path))
    try:
        status = target.stat()
        descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    except OSError as error:
        raise WriteError(error, replaced=False) from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fchmod(stream.fileno(), status.st_mode & 0o7777)
            os.fchown(stream.fileno(), status.st_uid, status.st_gid)
            os.fsync(stream.fileno())
        if target.read_bytes() != original:
            raise OSError("it changed while this ran (DMS may have saved it); re-run")
        os.replace(temporary, target)
    except OSError as error:
        Path(temporary).unlink(missing_ok=True)
        raise WriteError(error, replaced=False) from error
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    try:
        directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError as error:
        raise WriteError(error, replaced=True) from error


def main():
    args = sys.argv[1:]
    check_only = args[:1] == ["--check"]
    if check_only:
        args = args[1:]
    if len(args) != 1:
        raise SystemExit(__doc__)
    config_home = Path(args[0])
    path = config_home / "dms/settings.json"
    try:
        exists = path.is_file()
        original = path.read_bytes() if exists else None
        settings = parse_strict(str(path), original) if exists else None
        overlays = overlay_inputs(path.parent / "config.d")
        inputs = [(str(path), settings)] if exists else []
        inputs += overlays + policy_inputs() + environment_inputs(target_uids(config_home))
        modules = security_key_modules(settings)
    except (SettingsError, OSError) as error:
        print(f"[ERROR] {error}; cannot tell whether DMS requires a security key. "
              "Nothing was changed.", file=sys.stderr)
        return 1
    if modules:
        print("[ERROR] These PAM lines load a security-key module, which the managed "
              "stacks do not have:", file=sys.stderr)
        for line in modules:
            print(f"[ERROR]   {line}", file=sys.stderr)
        print("[ERROR] Switching DMS to the managed stacks could drop that factor. Remove the "
              "module from these stacks first if that is intended, then re-run. Nothing was "
              "changed.", file=sys.stderr)
        return 2
    found = security_key_settings(inputs)
    if found:
        return refuse(path, found, settings)
    if not exists:
        if not check_only:
            print(f"[WARN]  {path} not found; start DMS once, then re-run so the lock "
                  f"uses {MANAGED_LOCK} and the greeter keeps the managed PAM.", file=sys.stderr)
        return 3
    if not isinstance(settings, dict):
        print(f"[ERROR] {path} is not a JSON object. Nothing was changed.", file=sys.stderr)
        return 1
    if check_only:
        return 0
    changed = False
    # Stop DMS from rewriting /etc/pam.d/greetd (would drop Howdy) and its lock stack.
    for key in EXTERNAL_FLAGS:
        if settings.get(key) is not True:
            settings[key] = True
            changed = True
    # DMS 2.1 otherwise uses the distro login stack. Never replace a custom stack:
    # it may enforce more than this one (e.g. a second factor).
    lock_path = settings.get("lockPamPath") or ""
    if not lock_path:
        settings["lockPamPath"] = MANAGED_LOCK
        changed = True
    elif lock_path != MANAGED_LOCK:
        print(f"[WARN]  kept custom lockPamPath={lock_path}; the DMS lock does not use "
              f"{MANAGED_LOCK} or start Howdy automatically. Change it in DMS "
              "settings only if that stack should be replaced.", file=sys.stderr)
    for label, value in overlays:
        if isinstance(value, dict):
            for key in sorted(set(value) & {*EXTERNAL_FLAGS, "lockPamPath"}):
                print(f"[WARN]  {label} sets {key}, which DMS may apply over settings.json.", file=sys.stderr)
    # An alternative (not a second factor) that the external stack also turns off.
    if any(key.casefold() == "enablefprint" and not clearly_off(value, (False,))
           for _, input_value in inputs for key, value in keys_anywhere(input_value)):
        print("[WARN]  DMS's own fingerprint unlock is not offered while the lock PAM is "
              "externally managed.", file=sys.stderr)
    if not changed:
        print(f"[OK]    already set {path}")
        return 0
    try:
        write_atomically(path, settings, original)
    except WriteError as error:
        if error.replaced:
            print(f"[ERROR] {path} WAS changed (its PAM management settings), but flushing its "
                  f"directory failed: {error}. It may revert after a crash; re-run once the "
                  "cause is fixed.", file=sys.stderr)
        else:
            print(f"[ERROR] could not write {path}: {error}. The file is unchanged.", file=sys.stderr)
        return 1
    print(f"[OK]    updated {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
