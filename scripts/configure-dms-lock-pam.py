#!/usr/bin/env python3
"""Point DMS at the managed greeter/lock PAM stacks.

Usage: configure-dms-lock-pam.py [--check] CONFIG_HOME
CONFIG_HOME is the user's XDG config directory (usually ~/.config). DMS 2.1
reads CONFIG_HOME/dms/settings.json; ~/.config/DankMaterialShell is a legacy
path that DMS no longer reads, so it is never edited here. DMS merges
CONFIG_HOME/dms/config.d/*.json over settings.json in name order; those
overlays are read for the checks but never edited.
--check only reports a refusal and never writes.
Exit status: 0 done (or would be), 2 refused because DMS requires a security
key as a second factor, 3 the settings file does not exist yet. 2 and 3 change
nothing; any other status is an unexpected error.
"""

import json
from pathlib import Path
import sys

MANAGED_LOCK = "/etc/pam.d/dankshell"
EXTERNAL_FLAGS = ("greeterPamExternallyManaged", "lockPamExternallyManaged")


def requires_dms_security_key(data):
    # DMS runs its own security-key step after the password only while it
    # manages the lock PAM. With lockPamExternallyManaged it skips that step
    # (Modules/Lock/Pam.qml u2fSuppressedByPrimaryPam), and the managed
    # dankshell stack has no pam_u2f. u2fMode defaults to "or" in DMS.
    return data.get("enableU2f") is True and data.get("u2fMode", "or") == "and"


def effective_settings(settings_path):
    """settings.json with DMS 2.1's config.d overlays applied, as DMS merges them."""
    data = json.loads(settings_path.read_text(encoding="utf-8"))
    effective, sources = dict(data), {}
    overlays = settings_path.parent / "config.d"
    if overlays.is_dir():
        for overlay in sorted(overlays.glob("*.json")):
            values = json.loads(overlay.read_text(encoding="utf-8"))
            effective.update(values)
            sources.update(dict.fromkeys(values, overlay))
    return data, effective, sources


def main():
    args = sys.argv[1:]
    check_only = args[:1] == ["--check"]
    if check_only:
        args = args[1:]
    if len(args) != 1:
        raise SystemExit(__doc__)
    path = Path(args[0]) / "dms/settings.json"
    if not path.is_file():
        if check_only:
            return 3
        print(f"[WARN]  {path} not found; start DMS once, then re-run so the lock "
              f"uses {MANAGED_LOCK} and the greeter keeps the managed PAM.", file=sys.stderr)
        return 3
    data, effective, overlaid = effective_settings(path)
    if requires_dms_security_key(effective):
        already = effective.get("lockPamExternallyManaged") is True
        print(f"[ERROR] {path}: DMS requires a security key after the password "
              "(Lock Screen > Security key mode: Second factor (AND)). The managed lock "
              f"sets lockPamExternallyManaged=true, which makes DMS skip that step, "
              f"and {MANAGED_LOCK} has no pam_u2f, so the key would silently stop "
              "being required. Nothing was changed.", file=sys.stderr)
        if already:
            print("[ERROR] lockPamExternallyManaged is already true, so DMS is "
                  "skipping the key now; set it to false to restore the key.", file=sys.stderr)
        print("[ERROR] To use the managed password/face lock instead, switch the "
              "security key to Alternative (OR) or turn it off in DMS, then re-run.",
              file=sys.stderr)
        return 2
    if check_only:
        return 0
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
        if key in overlaid and effective[key] != data[key]:
            print(f"[WARN]  {overlaid[key]} sets {key}={effective[key]!r}, which DMS uses "
                  "instead of settings.json.", file=sys.stderr)
    # Alternatives (not second factors) that the external stack also turns off.
    dropped = [name for name, on in (("fingerprint", effective.get("enableFprint") is True),
                                     ("security key (OR)", effective.get("enableU2f") is True)) if on]
    if dropped:
        print(f"[WARN]  DMS's own {' and '.join(dropped)} unlock is not offered while "
              "the lock PAM is externally managed.", file=sys.stderr)
    if changed:
        # Rewrite in place so ownership, mode and ACLs of the user's file stay.
        with path.open("w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        print(f"[OK]    updated {path}")
    else:
        print(f"[OK]    already set {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
