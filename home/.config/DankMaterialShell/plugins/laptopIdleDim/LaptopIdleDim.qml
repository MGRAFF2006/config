import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Services

Scope {
    id: root

    property string pluginId: ""
    property var pluginService: null
    property int dimTimeout: 120
    property int dimPercent: 20
    property string dimmedDevice: ""
    property real previousBrightness: -1
    property real appliedDimPercent: 20
    readonly property bool servicesReady: DMSService.isConnected && BrightnessService.brightnessInitialized
    readonly property bool canDim: servicesReady && IdleService.enabled && !SessionService.idleInhibited
        && !DMSService.screensaverInhibited && !IdleService.monitorsOff && !IdleService.isShellLocked

    function dim() {
        if (!canDim || dimmedDevice)
            return;
        const device = BrightnessService.internalPanelDevice();
        if (!device)
            return;
        const brightness = BrightnessService.getDeviceBrightness(device.id);
        // Never brighten a panel that the user already set below the dim level.
        if (brightness <= dimPercent)
            return;
        dimmedDevice = device.id;
        previousBrightness = brightness;
        appliedDimPercent = dimPercent;
        // A shell crash must not turn the temporary dim level into the user's preference.
        if (pluginService)
            pluginService.savePluginData(pluginId, "pendingRestore", {device: device.id, brightness: brightness, dimPercent: dimPercent});
        BrightnessService.setBrightness(dimPercent, device.id, true);
    }

    function restore() {
        if (!dimmedDevice || !servicesReady)
            return;
        const device = dimmedDevice;
        const brightness = previousBrightness;
        dimmedDevice = "";
        previousBrightness = -1;
        // Preserve a brightness adjustment made while the panel was dimmed.
        if (Math.abs(BrightnessService.getDeviceBrightness(device) - appliedDimPercent) <= 1)
            BrightnessService.setBrightness(brightness, device, true);
        if (pluginService)
            pluginService.savePluginData(pluginId, "pendingRestore", null);
    }

    onCanDimChanged: {
        if (!canDim)
            restore();
    }
    onServicesReadyChanged: {
        if (servicesReady)
            restore();
    }
    Component.onCompleted: {
        const saved = pluginService ? pluginService.loadPluginData(pluginId, "pendingRestore", null) : null;
        if (saved && typeof saved.device === "string" && Number.isFinite(saved.brightness) && Number.isFinite(saved.dimPercent)) {
            dimmedDevice = saved.device;
            previousBrightness = saved.brightness;
            appliedDimPercent = saved.dimPercent;
            Qt.callLater(restore);
        }
    }
    Component.onDestruction: restore()

    IdleMonitor {
        timeout: root.dimTimeout
        enabled: root.canDim
        respectInhibitors: true
        onIsIdleChanged: {
            if (!enabled)
                return;
            if (isIdle)
                root.dim();
            else
                root.restore();
        }
    }
}
