#!/usr/bin/env python3
"""Apply Mathis's laptop-only DMS power defaults; no system files or sudo."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import os
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()
CONFIG = HOME / ".config/DankMaterialShell"
SETTINGS = {
    "batteryMonitorTimeout": 180,
    "batteryLockTimeout": 300,
    "batterySuspendTimeout": 900,
    "batteryPostLockMonitorTimeout": 20,
    "batterySuspendBehavior": 0,
    "batteryProfileName": "0",  # DMS stores Quickshell's PowerProfile enum as a string.
    "acMonitorTimeout": 180,
    "acLockTimeout": 300,
    "acSuspendTimeout": 1800,
    "acPostLockMonitorTimeout": 20,
    "acSuspendBehavior": 0,
    "acProfileName": "1",
    "lockBeforeSuspend": True,
    "loginctlLockIntegration": True,
    "keepAwakeBlocksSleep": True,
}


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def ipc(target, method, *args):
    return run("dms", "ipc", "call", target, method, *args)


def wait_for(check, message):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.1)
    raise SystemExit(message)


def write_settings(widgets):
    # DMS's IPC rejects lists. Its file watcher reloads one complete update,
    # including keys that this build's scalar IPC does not reliably persist.
    path = CONFIG / "settings.json"
    settings = json.loads(path.read_text())
    settings.update(SETTINGS)
    settings["controlCenterWidgets"] = widgets
    stat = path.stat()
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".power-settings-")
    try:
        os.fchmod(fd, stat.st_mode & 0o777)
        os.fchown(fd, -1, stat.st_gid)
        with os.fdopen(fd, "w") as stream:
            json.dump(settings, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    identity = json.loads(run("tailscale", "status", "--json"))["Self"]["HostName"]
    if identity != "laptop":
        raise SystemExit(f"Refusing laptop settings on {identity}")
    # Verify the running shell exposes the required settings before any writes.
    for key in SETTINGS:
        json.loads(ipc("settings", "get", key))
    widgets = json.loads(ipc("settings", "get", "controlCenterWidgets"))
    widgets = [w for w in widgets if (w.get("id") if isinstance(w, dict) else w) != "idleInhibitor"]
    widgets.append({"id": "idleInhibitor", "enabled": True, "w": 4, "h": 1})
    print("Dim at 2 min to 20%; display off at 3 min; lock at 5 min; suspend at 15/30 min (battery/AC).")
    print("Lid close suspends unless Keep Awake is on. Manual lock turns the display off after 20 s.")
    if not args.apply:
        print("Use --apply to back up and activate these laptop-only settings.")
        return
    keep_awake_was_on = "disabled" not in ipc("inhibit", "status")
    helper = HOME / ".local/bin/bt-a2dp-claim"
    if "BT_A2DP_INHIBIT_LID" not in helper.read_text():
        raise SystemExit("Deploy the updated home/.local/bin/bt-a2dp-claim before applying these defaults.")
    backup = HOME / ".local/state/config/laptop-power" / datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    backup.mkdir(parents=True, mode=0o700)
    for name in ("settings.json", "plugin_settings.json"):
        shutil.copy2(CONFIG / name, backup / name)
    units = ("laptop-lid-awake.service", "bt-a2dp-claim.service")
    states = {}
    for unit in units:
        states[unit] = {}
        for state in ("is-enabled", "is-active"):
            result = subprocess.run(["systemctl", "--user", state, unit], text=True, capture_output=True)
            states[unit][state] = result.stdout.strip()
    (backup / "services.json").write_text(json.dumps(states, indent=2) + "\n")
    print(f"Backup: {backup}", flush=True)
    plugin = CONFIG / "plugins/laptopIdleDim"
    source = ROOT / "home/.config/DankMaterialShell/plugins/laptopIdleDim"
    if plugin.exists() or plugin.is_symlink():
        if plugin.resolve() != source.resolve():
            raise SystemExit(f"Preserve existing plugin before replacing: {plugin}")
    else:
        plugin.symlink_to(source, target_is_directory=True)
    dropin = HOME / ".config/systemd/user/bt-a2dp-claim.service.d/50-laptop-power.conf"
    dropin.parent.mkdir(parents=True, exist_ok=True)
    if dropin.exists():
        shutil.copy2(dropin, backup / dropin.name)
    dropin.write_text("[Service]\nEnvironment=BT_A2DP_INHIBIT_LID=0\n")
    retired = HOME / ".config/systemd/user/laptop-lid-awake.service.d/50-dms-power.conf"
    retired.parent.mkdir(parents=True, exist_ok=True)
    if retired.exists():
        shutil.copy2(retired, backup / retired.name)
    # Older setup versions enable this unit. Make those reruns harmless too.
    retired.write_text("[Unit]\nConditionPathExists=!%h/.config/DankMaterialShell/plugins/laptopIdleDim/plugin.json\n")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    # Hold Keep Awake during migration so past idle time cannot suspend the session.
    ipc("inhibit", "enable")
    write_settings(widgets)
    wait_for(lambda: all(json.loads(ipc("settings", "get", k)) == v for k, v in SETTINGS.items()),
             "DMS did not reload the power defaults; Keep Awake remains on.")
    wait_for(lambda: any(w.get("id") == "idleInhibitor" for w in json.loads(ipc("settings", "get", "controlCenterWidgets")) if isinstance(w, dict)),
             "DMS did not reload the Keep Awake tile; Keep Awake remains on.")
    ipc("plugin-scan", "rescan")
    wait_for(lambda: "laptopIdleDim" in ipc("plugin-scan", "list"), "DMS did not discover the dimming plugin; Keep Awake remains on.")
    ipc("plugins", "enable", "laptopIdleDim")
    wait_for(lambda: "laptopIdleDim [loaded]" in ipc("plugins", "list"), "DMS did not load the dimming plugin; Keep Awake remains on.")
    # The native toggle must demonstrably own lid handling before retiring the old blocker.
    wait_for(lambda: any("Keep Awake" in line and "handle-lid-switch" in line for line in run("systemd-inhibit", "--list", "--no-pager").splitlines()),
             "Keep Awake did not acquire its lid inhibitor; old lid blocker was preserved.")
    subprocess.run(["systemctl", "--user", "disable", "--now", "laptop-lid-awake.service"], check=True)
    # systemctl disable also removes an externally linked unit's source link.
    legacy = HOME / ".config/systemd/user/laptop-lid-awake.service"
    if not legacy.exists() and not legacy.is_symlink():
        legacy.symlink_to(ROOT / "home/.config/systemd/user/laptop-lid-awake.service")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "restart", "bt-a2dp-claim.service"], check=True)
    if not keep_awake_was_on:
        ipc("inhibit", "disable")
    for key, value in SETTINGS.items():
        if json.loads(ipc("settings", "get", key)) != value:
            raise SystemExit(f"Setting did not persist: {key}")
    print(ipc("plugins", "status", "laptopIdleDim"))
    print("Applied. The coffee-cup Keep Awake tile is in Control Center.")
    print(ipc("inhibit", "status"))


if __name__ == "__main__":
    main()
