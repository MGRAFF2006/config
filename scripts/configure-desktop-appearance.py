#!/usr/bin/env python3
"""Apply readable wallpaper-themed glass, preserving widgets and unrelated settings."""

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime


CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
SETTINGS = CONFIG / "DankMaterialShell/settings.json"
LAYOUT = CONFIG / "hypr/dms/layout-user.lua"
INCLUDE = '\nrequire("dms.expressive")\n'
# DMS 2.0 omits barConfigs when it equals this default widget arrangement.
DEFAULT_BAR = {
    "id": "default", "name": "Main Bar", "enabled": True, "position": 0,
    "screenPreferences": ["all"], "showOnLastDisplay": True,
    "leftWidgets": ["launcherButton", "workspaceSwitcher", "focusedWindow"],
    "centerWidgets": ["music", "clock", "weather"],
    "rightWidgets": ["systemTray", "clipboard", "cpuUsage", "memUsage", "notificationButton", "battery", "controlCenterButton"],
}


def write_atomic(path, content):
    previous = path.stat()
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        os.fchmod(fd, previous.st_mode & 0o777)
        os.fchown(fd, -1, previous.st_gid)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--restore", type=Path, metavar="BACKUP")
    args = parser.parse_args()
    # Resolve symlinks before replacement, including a symlinked settings file.
    settings_path, layout_path = SETTINGS.resolve(strict=True), LAYOUT.resolve(strict=True)
    if args.restore:
        settings = json.loads((args.restore / "settings.json").read_text())
        layout = (args.restore / "layout-user.lua").read_text()
    else:
        settings = json.loads(settings_path.read_text())
        if not (CONFIG / "hypr/dms/expressive.lua").is_file():
            raise SystemExit("Deploy the Hyprland config with scripts/link-home.sh first.")
        settings.update({
            "currentThemeName": "dynamic", "currentThemeCategory": "dynamic",
            "matugenScheme": "scheme-tonal-spot", "matugenContrast": 0.25,
            "runDmsMatugenTemplates": True, "runUserMatugenTemplates": True,
            "matugenTemplateGtk": True, "matugenTemplateKcolorscheme": True,
            "matugenTemplateQt5ct": True, "matugenTemplateQt6ct": True,
            "matugenTemplateAlacritty": True, "matugenTemplateZenBrowser": True,
            "matugenTemplateNeovim": False,
            "iconThemeDark": "DMS-Papirus-Dark", "iconThemeLight": "DMS-Papirus",
            "iconThemePerMode": True,
            "popupTransparency": 0.72, "dockTransparency": 0.78,
            "blurEnabled": True, "blurForegroundLayers": True,
            "blurLayerOutlineOpacity": 0.16,
            "blurBorderEnabled": True, "blurBorderColor": "primary", "blurBorderOpacity": 0.30,
            "foregroundLayerTransparency": 0.72,
            "radiusMode": "scale", "radiusStrength": 65, "fontScale": 1.15,
            "hyprlandLayoutGapsOverride": 2, "hyprlandLayoutGapsOutOverride": 2,
            "hyprlandLayoutRadiusOverride": 4, "hyprlandLayoutBorderSize": 2,
            "animationDuration": 180, "syncComponentAnimationSpeeds": False,
            "popoutAnimationDuration": 130, "modalAnimationDuration": 160,
            "notificationAnimationDuration": 140,
            "springBounce": 0, "motionEffect": 0, "enableRippleEffects": True,
            "m3ElevationEnabled": True, "m3ElevationIntensity": 12, "m3ElevationOpacity": 35,
        })
        for bar in settings.setdefault("barConfigs", [DEFAULT_BAR]):
            bar.update({
                "spacing": 2, "innerPadding": 5, "barInsetPadding": 2,
                "bottomGap": 0, "transparency": 0.76, "widgetTransparency": 0.62,
                "fontScale": 1.1, "iconScale": 1.1,
                "squareCorners": False, "noBackground": False,
                "borderEnabled": True, "borderColor": "primary", "borderOpacity": 0.24,
                "borderThickness": 1, "widgetOutlineEnabled": False,
                "popupGapsAuto": False, "popupGapsManual": 8,
            })
            for widget in bar.get("leftWidgets", []):
                if isinstance(widget, dict) and widget.get("id") == "workspaceSwitcher":
                    for key in tuple(widget):
                        if key.endswith("CustomColor"):
                            del widget[key]
        layout = layout_path.read_text()
        if 'require("dms.expressive")' not in layout:
            layout += INCLUDE
    content = json.dumps(settings, indent=2) + "\n"
    if not (args.apply or args.restore):
        print(content)
        print("Preview only. Use --apply to save settings and enable the Hyprland effects.")
        return
    backup_root = STATE / "config/desktop-appearance-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y-%m-%d_%H-%M-%S-"), dir=backup_root))
    shutil.copy2(settings_path, backup / "settings.json")
    shutil.copy2(layout_path, backup / "layout-user.lua")
    print(f"Backup: {backup}", flush=True)
    print(f"Restore: python3 {Path(__file__).resolve()} --restore {backup}", flush=True)
    write_atomic(settings_path, content)
    write_atomic(layout_path, layout)
    print("Saved. DMS and Hyprland reload their configuration automatically.")


if __name__ == "__main__":
    main()
