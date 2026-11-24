#!/usr/bin/env python3
"""Check that applying and restoring the preset preserves personal configuration."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="desktop-appearance-check-") as directory:
        root = Path(directory)
        config, state = root / "config", root / "state"
        dms, hypr = config / "DankMaterialShell", config / "hypr/dms"
        dms.mkdir(parents=True)
        hypr.mkdir(parents=True)
        settings = {
            "currentThemeName": "blue", "unrelatedPreference": 42,
            "reduceMotion": True,
            "cursorSettings": {"theme": "System Default", "size": 36, "hyprland": {"hideOnKeyPress": True}},
            "barConfigs": [{"id": "personal", "leftWidgets": ["launcherButton", {"id": "workspaceSwitcher", "workspaceFocusedCustomColor": "#abcdef", "showOccupiedWorkspacesOnly": True}], "rightWidgets": ["tuVpn", "networkDiagnostics"], "position": 2}],
        }
        # Resolve a settings-file symlink without replacing the link itself.
        target = root / "settings-target.json"
        target.write_text(json.dumps(settings))
        target.chmod(0o640)
        (dms / "settings.json").symlink_to(target)
        original_layout = "-- Personal layout\nhl.config({general = {gaps_in = 2}})\n"
        (hypr / "layout-user.lua").write_text(original_layout)
        shutil.copy2(ROOT / "home/.config/hypr/dms/expressive.lua", hypr / "expressive.lua")
        env = dict(os.environ, XDG_CONFIG_HOME=str(config), XDG_STATE_HOME=str(state))

        def run(*args, success=True):
            result = subprocess.run(["python3", str(ROOT / "scripts/configure-desktop-appearance.py"), *args], env=env, capture_output=True, text=True)
            assert (result.returncode == 0) == success, result.stdout + result.stderr
            return result

        before = target.read_bytes()
        run()
        assert target.read_bytes() == before and not state.exists()
        run("--apply")
        backup = next((state / "config/desktop-appearance-backups").iterdir())
        changed = json.loads(target.read_text())
        assert changed["currentThemeName"] == "dynamic"
        assert changed["unrelatedPreference"] == 42 and changed["reduceMotion"] is True
        assert changed["cursorSettings"] == {"theme": "breeze_cursors", "size": 36, "hyprland": {"hideOnKeyPress": True}}
        bar = changed["barConfigs"][0]
        assert bar["rightWidgets"] == settings["barConfigs"][0]["rightWidgets"]
        assert bar["id"] == "personal" and bar["position"] == 2
        assert bar["leftWidgets"][1]["showOccupiedWorkspacesOnly"] is True
        assert "workspaceFocusedCustomColor" not in bar["leftWidgets"][1]
        assert (dms / "settings.json").is_symlink() and target.stat().st_mode & 0o777 == 0o640
        applied = target.read_bytes()
        run("--apply")
        assert target.read_bytes() == applied
        assert (hypr / "layout-user.lua").read_text().count('require("dms.expressive")') == 1
        run("--restore", str(backup))
        assert json.loads(target.read_text()) == settings
        assert (hypr / "layout-user.lua").read_text() == original_layout
        target.write_text(json.dumps({"configVersion": 42, "currentThemeName": "blue"}))
        run("--apply")
        sparse = json.loads(target.read_text())
        assert sparse["currentThemeName"] == "dynamic"
        assert sparse["barConfigs"][0]["leftWidgets"] == ["launcherButton", "workspaceSwitcher", "focusedWindow"]
        assert sparse["barConfigs"][0]["centerWidgets"] == ["music", "clock", "weather"]
        assert sparse["barConfigs"][0]["rightWidgets"] == ["systemTray", "clipboard", "cpuUsage", "memUsage", "notificationButton", "battery", "controlCenterButton"]
        target.write_text(json.dumps({"cursorSettings": {"theme": "Personal Cursor", "size": 48}}))
        run("--apply")
        assert json.loads(target.read_text())["cursorSettings"] == {"theme": "Personal Cursor", "size": 48}
        # Restore before checking refusal, so the layout must remain untouched.
        run("--restore", str(backup))
        target.write_text("{corrupt")
        run("--apply", success=False)
        assert target.read_text() == "{corrupt"
        assert (hypr / "layout-user.lua").read_text() == original_layout
    print("PASS: preset preserves widgets/preferences, permissions/symlinks, repeat apply, restore, corrupt-input refusal")


if __name__ == "__main__":
    main()
