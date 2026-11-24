#!/usr/bin/env python3
"""Point DMS at the managed greeter/lock PAM stacks.

Usage: configure-dms-lock-pam.py [--check] CONFIG_HOME
CONFIG_HOME is the user's XDG config directory (usually ~/.config). DMS 2.1
reads CONFIG_HOME/dms/settings.json; ~/.config/DankMaterialShell is a legacy
path that DMS no longer reads, so it is never edited here. DMS merges
CONFIG_HOME/dms/config.d/*.json over settings.json, then the administrator's
lock_settings policy over both; those are read for the checks but never edited.
--check only reports a refusal and never writes.
Exit status: 0 done (or would be), 2 refused because DMS requires a security
key as a second factor, 3 the settings file does not exist yet. 2 and 3 change
nothing; any other status is an error, and the settings file is then unchanged.
"""

from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import sys
import tempfile

MANAGED_LOCK = "/etc/pam.d/dankshell"
EXTERNAL_FLAGS = ("greeterPamExternallyManaged", "lockPamExternallyManaged")
# DMS 2.1.2 core/internal/clipolicy: packaged first, the administrator's file over it.
POLICY_PATHS = (Path("/usr/share/dms/cli-policy.json"), Path("/etc/dms/cli-policy.json"))
POLICY_ENV = "DMS_POLICY_LOCK_SETTINGS"
# clipolicy's lockSettingKeys: the only keys lock_settings may manage.
LOCK_SETTING_KEYS = frozenset((
    "customPowerActionLock", "lockBeforeSuspend", "loginctlLockIntegration", "lockAtStartup",
    "acLockTimeout", "batteryLockTimeout", "fadeToLockEnabled", "fadeToLockGracePeriod",
    "enableFprint", "maxFprintTries", "enableU2f", "u2fMode",
))
# The shell drops a managed value whose JSON type differs from the setting's
# default (Common/settings/ManagedSettings.js); these are the ones read here.
SETTING_TYPES = {"enableU2f": bool, "enableFprint": bool, "u2fMode": str}


class SettingsError(Exception):
    pass


def js_truthy(value):
    # QML converts a JSON value to a bool property with JavaScript truthiness.
    return value not in (None, False, 0, "")


def requires_dms_security_key(settings):
    # DMS runs its own security-key step after the password only while it
    # manages the lock PAM. With lockPamExternallyManaged it skips that step
    # (Modules/Lock/Pam.qml u2fSuppressedByPrimaryPam), and the managed
    # dankshell stack has no pam_u2f. u2fMode defaults to "or" in DMS.
    return js_truthy(settings.get("enableU2f")) and settings.get("u2fMode", "or") == "and"


def read_object(path, empty_ok):
    try:
        text = path.read_text(encoding="utf-8")
        value = json.loads(text) if text.strip() or not empty_ok else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SettingsError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise SettingsError(f"{path} is not a JSON object")
    return value


def overlay_files(directory):
    """config.d files as DMS 2.1.2 loads them (Common/SettingsData.qml): a
    FolderListModel with nameFilters ["*.json"] (case-sensitive), showDirs false
    and showHidden false, applied in the JavaScript string order of their paths,
    which compares UTF-16 code units."""
    if not directory.is_dir():
        return []
    found = [entry for entry in directory.iterdir()
             if not entry.name.startswith(".") and fnmatchcase(entry.name, "*.json") and entry.is_file()]
    return sorted(found, key=lambda entry: entry.name.encode("utf-16-be", "surrogatepass"))


def policy_lock_settings():
    """lock_settings from the packaged and administrator policy, merged per key
    as `dms run` passes them to the shell. DMS ignores every lock setting when a
    policy file is unreadable; this refuses instead of guessing."""
    settings, sources = {}, {}
    for path in POLICY_PATHS:
        if not path.exists():
            continue
        policy = read_object(path, empty_ok=False)
        values = policy.get("lock_settings")
        if values is None:
            values = {}
        if not isinstance(values, dict):
            raise SettingsError(f"{path}: lock_settings is not a JSON object")
        for key, value in values.items():
            if key in LOCK_SETTING_KEYS and value is not None:
                settings[key], sources[key] = value, f"policy {path} (lock_settings)"
    return settings, sources


def env_lock_settings():
    """The shell applies DMS_POLICY_LOCK_SETTINGS from its environment. `dms run`
    always sets it from the policy files, but a shell started another way keeps
    an inherited value, so a value set here counts as well."""
    text = os.environ.get(POLICY_ENV)
    if not text:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise SettingsError(f"cannot read {POLICY_ENV}: {error}") from error
    if not isinstance(value, dict):
        raise SettingsError(f"{POLICY_ENV} is not a JSON object")
    return value


def apply_lock_settings(settings, sources, managed, managed_sources):
    effective, origin = dict(settings), dict(sources)
    for key, value in managed.items():
        expected = SETTING_TYPES.get(key)
        if expected is not None and type(value) is not expected:
            continue
        effective[key], origin[key] = value, managed_sources[key]
    return effective, origin


def effective_settings(settings_path):
    """settings.json, then config.d overlays (shallow, as DMS merges them), then
    each lock_settings policy that may apply. Returns the user's own settings and
    one (settings, sources) pair per policy view."""
    data = read_object(settings_path, empty_ok=True) if settings_path.is_file() else {}
    merged, sources = dict(data), dict.fromkeys(data, settings_path)
    for overlay in overlay_files(settings_path.parent / "config.d"):
        values = read_object(overlay, empty_ok=True)
        merged.update(values)
        sources.update(dict.fromkeys(values, overlay))
    views = [apply_lock_settings(merged, sources, *policy_lock_settings())]
    env_policy = env_lock_settings()
    if env_policy is not None:
        views.append(apply_lock_settings(merged, sources, env_policy, dict.fromkeys(env_policy, f"${POLICY_ENV}")))
    return data, views


def write_atomically(path, data):
    """Replace the file as DMS itself saves it (QSaveFile): a temporary file in the
    same directory, flushed to disk, then renamed over it. A failure leaves the
    original untouched. Mode and owner are kept; a symlink keeps pointing at it."""
    target = Path(os.path.realpath(path))
    status = target.stat()
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fchmod(stream.fileno(), status.st_mode & 0o7777)
            os.fchown(stream.fileno(), status.st_uid, status.st_gid)
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def refuse(path, effective, origin):
    sources = sorted({str(origin[key]) for key in ("enableU2f", "u2fMode")})
    print(f"[ERROR] {path}: DMS requires a security key after the password "
          "(Lock Screen > Security key mode: Second factor (AND)), set by "
          f"{' and '.join(sources)}. The managed lock sets lockPamExternallyManaged=true, "
          f"which makes DMS skip that step, and {MANAGED_LOCK} has no pam_u2f, so the key "
          "would silently stop being required. Nothing was changed.", file=sys.stderr)
    if effective.get("lockPamExternallyManaged") is True:
        print("[ERROR] lockPamExternallyManaged is already true, so DMS is "
              "skipping the key now; set it to false to restore the key.", file=sys.stderr)
    print("[ERROR] To use the managed password/face lock instead, switch the "
          "security key to Alternative (OR) or turn it off where it is set, then re-run.",
          file=sys.stderr)
    return 2


def main():
    args = sys.argv[1:]
    check_only = args[:1] == ["--check"]
    if check_only:
        args = args[1:]
    if len(args) != 1:
        raise SystemExit(__doc__)
    path = Path(args[0]) / "dms/settings.json"
    try:
        data, views = effective_settings(path)
    except SettingsError as error:
        print(f"[ERROR] {error}; cannot tell whether DMS requires a security key. "
              "Nothing was changed.", file=sys.stderr)
        return 1
    for effective, origin in views:
        if requires_dms_security_key(effective):
            return refuse(path, effective, origin)
    if not path.is_file():
        if not check_only:
            print(f"[WARN]  {path} not found; start DMS once, then re-run so the lock "
                  f"uses {MANAGED_LOCK} and the greeter keeps the managed PAM.", file=sys.stderr)
        return 3
    if check_only:
        return 0
    effective, origin = views[0]
    changed = False
    # Stop DMS from rewriting /etc/pam.d/greetd (would drop Howdy) and its lock stack.
    for key in EXTERNAL_FLAGS:
        if data.get(key) is not True:
            data[key] = True
            changed = True
    # DMS 2.1 otherwise uses the distro login stack. Never replace a custom stack:
    # it may enforce more than this one (e.g. a second factor).
    lock_path = data.get("lockPamPath") or ""
    if not lock_path:
        data["lockPamPath"] = MANAGED_LOCK
        changed = True
    elif lock_path != MANAGED_LOCK:
        print(f"[WARN]  kept custom lockPamPath={lock_path}; the DMS lock does not use "
              f"{MANAGED_LOCK} or start Howdy automatically. Change it in DMS "
              "settings only if that stack should be replaced.", file=sys.stderr)
    for key in (*EXTERNAL_FLAGS, "lockPamPath"):
        if origin.get(key) not in (None, path) and effective[key] != data[key]:
            print(f"[WARN]  {origin[key]} sets {key}={effective[key]!r}, which DMS uses "
                  "instead of settings.json.", file=sys.stderr)
    # Alternatives (not second factors) that the external stack also turns off.
    dropped = [name for name, on in (("fingerprint", js_truthy(effective.get("enableFprint"))),
                                     ("security key (OR)", js_truthy(effective.get("enableU2f")))) if on]
    if dropped:
        print(f"[WARN]  DMS's own {' and '.join(dropped)} unlock is not offered while "
              "the lock PAM is externally managed.", file=sys.stderr)
    if not changed:
        print(f"[OK]    already set {path}")
        return 0
    try:
        write_atomically(path, data)
    except OSError as error:
        print(f"[ERROR] could not write {path}: {error}. The file is unchanged.", file=sys.stderr)
        return 1
    print(f"[OK]    updated {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
