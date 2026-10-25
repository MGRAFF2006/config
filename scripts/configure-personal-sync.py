#!/usr/bin/env python3
"""Keep personal files in Syncthing; use Git for software checkouts."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BEGIN = "// BEGIN managed personal-file scope"
END = "// END managed personal-file scope"


def api_client(home):
    state = Path(os.environ.get("XDG_STATE_HOME", home / ".local/state"))
    config = ET.parse(state / "syncthing/config.xml").getroot()
    key = config.findtext("gui/apikey")
    if not key:
        raise ValueError("Syncthing GUI API key is missing")
    # This kit's Syncthing GUI listens on loopback, never a remote API.
    def api(path, data=None, method="GET"):
        request = urllib.request.Request(
            "http://127.0.0.1:8384/rest/" + path,
            data=None if data is None else json.dumps(data).encode(),
            headers={"X-API-Key": key, "Content-Type": "application/json"},
            method=method,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None
    return api, state


def folder_endpoint(folder_id):
    return "config/folders/" + urllib.parse.quote(folder_id, safe="")


def scope_plan(folders, home, policy):
    roots = [(home / rel).resolve() for rel in policy["git_only"]]
    removed, retained = [], []
    for folder in folders:
        path = Path(os.path.expanduser(folder["path"])).resolve()
        if any(path == root or root in path.parents for root in roots):
            removed.append(folder)
        else:
            patterns = ["/" + root.relative_to(path).as_posix()
                        for root in roots if path in root.parents]
            retained.append((folder, patterns + policy["generated"]))
    return removed, retained


def managed_ignores(previous, patterns):
    previous = previous or []
    if BEGIN in previous or END in previous:
        if previous.count(BEGIN) != 1 or previous.count(END) != 1:
            raise ValueError("Malformed managed ignore block; refusing to replace it")
        start, end = previous.index(BEGIN), previous.index(END)
        if end < start:
            raise ValueError("Malformed managed ignore block order")
        previous = previous[:start] + previous[end + 1:]
    # First match wins: put managed code/cache exclusions before local overrides.
    return [BEGIN, *patterns, END, *previous]


def apply_scope(api, home, policy, state, apply):
    folders = api("config/folders")
    removed, retained = scope_plan(folders, home, policy)
    changes = []
    for folder, patterns in retained:
        endpoint = "db/ignores?folder=" + urllib.parse.quote(folder["id"], safe="")
        previous = api(endpoint).get("ignore") or []
        desired = managed_ignores(previous, patterns)
        if desired != previous:
            changes.append({"id": folder["id"], "path": folder["path"],
                            "before": previous, "after": desired})
    for folder in removed:
        print(f"Remove sync registration (keep files): {folder['id']} {folder['path']}")
    for change in changes:
        print(f"Exclude software and generated caches: {change['id']} {change['path']}")
    if not apply:
        print("Preview only; run with --apply to save a backup and change scope.")
        return
    if not removed and not changes:
        print("Personal-file scope already applied.")
        return
    parent = state / "config"
    parent.mkdir(parents=True, exist_ok=True)
    backup_dir = Path(tempfile.mkdtemp(prefix="personal-sync-before-" + datetime.now().date().isoformat() + "-", dir=parent))
    backup = backup_dir / "scope.json"
    snapshot = {"device": api("system/status")["myID"], "removed": removed, "ignores": changes}
    with backup.open("x") as stream:
        json.dump(snapshot, stream, indent=2)
        stream.write("\n")
    backup.chmod(0o600)
    print(f"Restore previous scope: python3 {ROOT / 'scripts/configure-personal-sync.py'} --restore {backup}", flush=True)
    # Stop syncing Git checkouts before writing any remaining ignore files.
    for folder in removed:
        api(folder_endpoint(folder["id"]), method="DELETE")
    for change in changes:
        api("db/ignores?folder=" + urllib.parse.quote(change["id"], safe=""),
            {"ignore": change["after"]}, "POST")
    print("Applied personal-file scope; local files were not deleted or moved.")


def restore_scope(api, backup):
    snapshot = json.loads(backup.read_text())
    if api("system/status")["myID"] != snapshot["device"]:
        raise ValueError("Backup belongs to another Syncthing device")
    current = {f["id"]: f for f in api("config/folders")}
    # Refuse conflicts before making any restoration changes.
    for folder in snapshot["removed"]:
        if folder["id"] in current and current[folder["id"]] != folder:
            raise ValueError(f"Folder configuration changed since backup: {folder['id']}")
    for change in snapshot["ignores"]:
        if change["id"] not in current or current[change["id"]]["path"] != change["path"]:
            raise ValueError(f"Folder path changed since backup: {change['id']}")
        present = api("db/ignores?folder=" + urllib.parse.quote(change["id"], safe="")).get("ignore") or []
        if present not in (change["before"], change["after"]):
            raise ValueError(f"Ignore rules changed since backup: {change['id']}")
    for folder in snapshot["removed"]:
        if folder["id"] not in current:
            api("config/folders", folder, "POST")
    for change in snapshot["ignores"]:
        api("db/ignores?folder=" + urllib.parse.quote(change["id"], safe=""),
            {"ignore": change["before"]}, "POST")
    print("Restored previous folder registrations and ignore rules.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--restore", type=Path, metavar="BACKUP")
    args = parser.parse_args()
    home = Path.home()
    api, state = api_client(home)
    if args.restore:
        restore_scope(api, args.restore)
    else:
        policy = json.loads((ROOT / "syncthing/personal-files.json").read_text())
        apply_scope(api, home, policy, state, args.apply)


if __name__ == "__main__":
    main()
