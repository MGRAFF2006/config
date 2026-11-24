#!/usr/bin/env python3
"""Exercise the production QML dimmer with fake backlight and session services."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {
    "BrightnessService": """
property real brightness: 60
property bool brightnessInitialized: true
property bool panelAvailable: true
property int writes: 0
function internalPanelDevice() { return panelAvailable ? { id: 'internal' } : null; }
function getDeviceBrightness(device) { return brightness; }
function setBrightness(value, device, suppress) { brightness = value; writes++; }
""",
    "DMSService": """
property bool screensaverInhibited: false
property bool isConnected: true
""",
    "SessionService": """
property bool idleInhibited: false
""",
    "IdleService": """
property bool enabled: true
property bool monitorsOff: false
property bool isShellLocked: false
""",
}
HARNESS = """
import QtQuick
import Quickshell
import qs.Services
ShellRoot {
    QtObject {
        id: store
        property var snapshot: null
        function savePluginData(id, key, value) { snapshot = value; }
        function loadPluginData(id, key, fallback) { return snapshot; }
    }
    LaptopIdleDim { id: dimmer; dimTimeout: 120; pluginService: store }
    function check(condition, message) {
        if (!condition) throw new Error(message);
    }
    Component.onCompleted: Qt.callLater(() => {
        try {
            dimmer.dim(); check(BrightnessService.brightness === 20, 'idle must dim');
            check(store.snapshot.brightness === 60, 'save brightness before dimming');
            dimmer.restore(); check(BrightnessService.brightness === 60, 'activity must restore');
            BrightnessService.brightness = 10;
            dimmer.dim(); check(BrightnessService.brightness === 10, 'never brighten a dark panel');
            BrightnessService.brightness = 55;
            dimmer.dim(); BrightnessService.brightness = 35;
            dimmer.restore(); check(BrightnessService.brightness === 35, 'preserve manual adjustment');
            SessionService.idleInhibited = true;
            dimmer.dim(); check(BrightnessService.brightness === 35, 'Keep Awake must prevent dimming');
            SessionService.idleInhibited = false;
            dimmer.dim(); SessionService.idleInhibited = true;
            check(BrightnessService.brightness === 35, 'Keep Awake must restore an already dimmed panel');
            SessionService.idleInhibited = false;
            DMSService.screensaverInhibited = true;
            dimmer.dim(); check(BrightnessService.brightness === 35, 'respect media inhibitors');
            DMSService.screensaverInhibited = false;
            dimmer.dim(); IdleService.monitorsOff = true;
            check(BrightnessService.brightness === 35, 'restore while display is off for next wake');
            IdleService.monitorsOff = false;
            BrightnessService.panelAvailable = false;
            dimmer.dim(); check(dimmer.dimmedDevice === '', 'no external-monitor dimming');
            BrightnessService.panelAvailable = true;
            dimmer.dim(); DMSService.isConnected = false;
            dimmer.restore(); check(store.snapshot.brightness === 35, 'retain restore data during disconnect');
            DMSService.isConnected = true;
            check(BrightnessService.brightness === 35 && store.snapshot === null, 'recover after reconnect');
            store.snapshot = {device: 'internal', brightness: 70, dimPercent: 20};
            BrightnessService.brightness = 20;
            const restarted = Qt.createComponent('LaptopIdleDim.qml').createObject(null, {pluginService: store});
            check(restarted !== null, 'instantiate restart recovery');
            Qt.callLater(() => {
                try {
                    check(BrightnessService.brightness === 70 && store.snapshot === null, 'restore after a shell crash');
                    console.info('PASS: dim/restore, manual adjustments, inhibitors, internal panel, disconnect and restart recovery');
                } catch (error) { console.error('FAIL: ' + error.message); }
                restarted.destroy();
                Qt.quit();
            });
            return;
        } catch (error) {
            console.error('FAIL: ' + error.message);
        }
        Qt.quit();
    })
}
"""

with tempfile.TemporaryDirectory(prefix="laptop-dim-check-") as temporary:
    target = Path(temporary)
    services = target / "Services"
    services.mkdir()
    (services / "qmldir").write_text("module qs.Services\n" + "".join(f"singleton {name} 1.0 {name}.qml\n" for name in SERVICES))
    for name, body in SERVICES.items():
        (services / (name + ".qml")).write_text("pragma Singleton\nimport QtQuick\nQtObject {\n" + body + "\n}\n")
    shutil.copy2(ROOT / "home/.config/DankMaterialShell/plugins/laptopIdleDim/LaptopIdleDim.qml", target)
    (target / "shell.qml").write_text(HARNESS)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    env.pop("WAYLAND_DISPLAY", None)
    result = subprocess.run(["qs", "-p", str(target / "shell.qml"), "--no-color"], env=env, capture_output=True, text=True, timeout=15)
    output = result.stdout + result.stderr
    if result.returncode or "FAIL:" in output or "PASS:" not in output:
        raise SystemExit(output)
    print(next(line for line in output.splitlines() if "PASS:" in line))
    print("Hardware and session services were isolated; the real Wayland idle timer is checked separately.")
