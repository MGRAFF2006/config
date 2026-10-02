#!/usr/bin/env python3
"""Enable the dedicated network panel and DMS's standard audio controls."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "DankMaterialShell"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
PLUGIN_SETTINGS_PATH = CONFIG_DIR / "plugin_settings.json"
BAR_PLUGIN = "networkDiagnostics"
CONTROL_CENTER_FLAGS_OFF = (
    "controlCenterShowNetworkIcon",
    "controlCenterShowBluetoothIcon",
    "controlCenterShowVpnIcon",
    "controlCenterShowBrightnessIcon",
    "controlCenterShowBatteryIcon",
    "controlCenterShowPrinterIcon",
    "controlCenterShowScreenSharingIcon",
    "controlCenterShowIdleInhibitorIcon",
    "controlCenterShowDoNotDisturbIcon",
)
STANDARD_AUDIO_WIDGETS = (
    {"id": "volumeSlider", "enabled": True, "width": 50},
    {"id": "audioOutput", "enabled": True, "width": 50},
    {"id": "audioInput", "enabled": True, "width": 50},
)
SESSION_PATH = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "DankMaterialShell/session.json"


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return default


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as file:
            json.dump(value, file, indent=2)
            file.write("\n")
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def widget_id(widget: Any) -> str:
    if isinstance(widget, str):
        return widget
    if isinstance(widget, dict):
        return str(widget.get("id", ""))
    return ""


def configure_settings() -> None:
    settings = read_json(SETTINGS_PATH, {})
    if not isinstance(settings, dict):
        raise SystemExit(f"Invalid DMS settings: {SETTINGS_PATH}")

    settings["showControlCenterButton"] = True
    settings["blurEnabled"] = True
    settings["blurForegroundLayers"] = True
    settings["blurLayerOutlineOpacity"] = 0.12
    settings["blurBorderEnabled"] = True
    settings["blurBorderOpacity"] = 0.28
    settings["popupTransparency"] = 0.88
    settings["dockTransparency"] = 0.88
    for key in CONTROL_CENTER_FLAGS_OFF:
        settings[key] = False
    settings["controlCenterShowAudioIcon"] = True
    settings["controlCenterShowMicIcon"] = False

    widgets = settings.get("controlCenterWidgets", [])
    if not isinstance(widgets, list):
        widgets = []
    audio_ids = {widget["id"] for widget in STANDARD_AUDIO_WIDGETS}
    widgets = [
        widget
        for widget in widgets
        if widget_id(widget) not in audio_ids
        and widget_id(widget) not in ("plugin_audioMixer", "audioRouter")
    ]
    widgets.insert(0, dict(STANDARD_AUDIO_WIDGETS[0]))
    audio_device_position = next(
        (index + 1 for index, widget in enumerate(widgets) if widget_id(widget) == "bluetooth"),
        1,
    )
    widgets[audio_device_position:audio_device_position] = [
        dict(STANDARD_AUDIO_WIDGETS[1]),
        dict(STANDARD_AUDIO_WIDGETS[2]),
    ]
    settings["controlCenterWidgets"] = widgets

    for bar in settings.get("barConfigs", []):
        if not isinstance(bar, dict):
            continue
        bar["transparency"] = 0.88
        bar["widgetTransparency"] = 0.78
        right = bar.get("rightWidgets", [])
        if not isinstance(right, list):
            continue
        right = [
            widget for widget in right
            if widget_id(widget) not in (BAR_PLUGIN, "audioMixer", "audioRouter")
        ]
        insert_at = next(
            (index for index, widget in enumerate(right) if widget_id(widget) == "controlCenterButton"),
            len(right),
        )
        right.insert(insert_at, BAR_PLUGIN)
        bar["rightWidgets"] = right
        for widget in right:
            if not isinstance(widget, dict) or widget_id(widget) != "controlCenterButton":
                continue
            widget.update(
                {
                    "showNetworkIcon": False,
                    "showBluetoothIcon": False,
                    "showAudioIcon": False,
                    "showVpnIcon": False,
                    "showBrightnessIcon": False,
                    "showMicIcon": True,
                    "showBatteryIcon": False,
                    "showPrinterIcon": False,
                    "showScreenSharingIcon": False,
                    "showIdleInhibitorIcon": False,
                    "showDoNotDisturbIcon": False,
                }
            )

    write_json_atomic(SETTINGS_PATH, settings)


def forget_internal_audio_devices() -> None:
    session = read_json(SESSION_PATH, {})
    if not isinstance(session, dict):
        return
    hidden = session.get("hiddenOutputDeviceNames", [])
    if not isinstance(hidden, list):
        hidden = []
    session["hiddenOutputDeviceNames"] = [
        name for name in hidden if not str(name).startswith("dms_mixer_")
    ]
    write_json_atomic(SESSION_PATH, session)


def enable_plugins() -> None:
    settings = read_json(PLUGIN_SETTINGS_PATH, {})
    if not isinstance(settings, dict):
        settings = {}
    plugin = settings.setdefault(BAR_PLUGIN, {})
    if not isinstance(plugin, dict):
        plugin = {}
        settings[BAR_PLUGIN] = plugin
    plugin["enabled"] = True
    settings.pop("audioMixer", None)
    settings.pop("audioRouter", None)
    write_json_atomic(PLUGIN_SETTINGS_PATH, settings)


def main() -> int:
    if not SETTINGS_PATH.exists():
        raise SystemExit(f"DMS settings not found: {SETTINGS_PATH}")
    configure_settings()
    forget_internal_audio_devices()
    enable_plugins()
    print("Configured network diagnostics and restored DMS's standard audio controls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
