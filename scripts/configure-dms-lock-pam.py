#!/usr/bin/env python3
"""Point DMS at the managed greeter/lock PAM stacks.

Usage: configure-dms-lock-pam.py CONFIG_HOME
CONFIG_HOME is the user's XDG config directory (usually ~/.config). DMS 2.1
reads CONFIG_HOME/dms/settings.json; ~/.config/DankMaterialShell is a legacy
path that DMS no longer reads, so it is never edited here.
Exits 1 without changes when the settings file does not exist yet.
"""

import json
from pathlib import Path
import sys

MANAGED_LOCK = "/etc/pam.d/dankshell"


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    path = Path(sys.argv[1]) / "dms/settings.json"
    if not path.is_file():
        print(f"[WARN]  {path} not found; start DMS once, then re-run so the lock "
              f"uses {MANAGED_LOCK} and the greeter keeps the managed PAM.", file=sys.stderr)
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    # Stop DMS from rewriting /etc/pam.d/greetd (would drop Howdy) and its lock stack.
    for key in ("greeterPamExternallyManaged", "lockPamExternallyManaged"):
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
