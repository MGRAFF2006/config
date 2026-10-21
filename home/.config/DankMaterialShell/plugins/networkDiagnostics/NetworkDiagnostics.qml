import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Common
import qs.Services
import qs.Widgets
import qs.Modules.Plugins
import qs.Modules.ControlCenter.Details as NetworkDetails

PluginComponent {
    id: root

    Ref { service: NetworkService }

    readonly property bool stateReady: NetworkService.stateInitialized && (NetworkService.usingLegacy || (DMSService.isConnected && DMSService.subscribeConnected))
    readonly property bool linkConnected: stateReady && (NetworkService.wifiConnected || NetworkService.ethernetConnected)
    readonly property bool wired: NetworkService.networkStatus === "ethernet" || (!NetworkService.wifiConnected && NetworkService.ethernetConnected)
    readonly property string interfaceName: wired ? NetworkService.ethernetInterface : NetworkService.wifiInterface
    readonly property string connectionName: wired ? (NetworkService.primaryConnection || "Ethernet") : NetworkService.currentWifiSSID
    readonly property string connectionKey: [stateReady, linkConnected, wired, interfaceName, connectionName].join("|")
    readonly property string connectionTitle: !stateReady ? "Checking connection…" : linkConnected ? (connectionName || (wired ? "Ethernet" : "Wi-Fi")) : NetworkService.isConnecting ? "Connecting…" : !NetworkService.wifiEnabled ? "Wi-Fi is off" : "Disconnected"
    readonly property string connectionIcon: !stateReady ? "sync" : linkConnected ? (wired ? "lan" : NetworkService.wifiSignalIcon) : "wifi_off"
    readonly property bool sampleMatches: linkConnected && networkData.connected === true && networkData.interface === interfaceName
    readonly property bool sampleFresh: sampleMatches && updatedAt > 0 && clockTime - updatedAt < 25000
    readonly property string connectivity: sampleFresh ? (networkData.connectivity || "unknown") : "unknown"
    readonly property string internetStatus: !stateReady ? "Waiting for network status" : !linkConnected ? "No active network connection" : connectivity === "full" ? "Internet available" : connectivity === "portal" ? "Network sign-in may be required" : connectivity === "limited" ? "Limited internet access reported" : connectivity === "none" ? "No internet access reported" : "Internet access not checked"
    readonly property bool internetWarning: linkConnected && ["portal", "limited", "none"].includes(connectivity)
    readonly property string barText: !stateReady ? "…" : !linkConnected ? (NetworkService.isConnecting ? "…" : "Disconnected") : sampleFresh && networkData.internetPingMs !== null && networkData.internetPingMs !== undefined ? latency(networkData.internetPingMs) : wired ? "Ethernet" : "Wi-Fi"

    property int connectionRevision: 0
    property var networkData: ({})
    property var trafficHistory: []
    property bool refreshing: false
    property string refreshError: ""
    property double updatedAt: 0
    property double clockTime: Date.now()
    readonly property string statusCommand: (Quickshell.env("HOME") || "") + "/.local/bin/dms-network-status"

    onConnectionKeyChanged: {
        connectionRevision++;
        networkData = {};
        trafficHistory = [];
        updatedAt = 0;
        refreshError = "";
        if (stateReady) Qt.callLater(refresh);
    }

    function refresh() {
        if (refreshing) return;
        refreshing = true;
        const requestRevision = connectionRevision;
        const screenKey = parentScreen?.name || "default";
        const command = linkConnected && interfaceName ? [statusCommand, "--interface", interfaceName] : [statusCommand];
        Proc.runCommand("networkDiagnostics.status." + screenKey, command, (stdout, exitCode) => {
            refreshing = false;
            if (requestRevision !== connectionRevision) {
                Qt.callLater(refresh);
                return;
            }
            if (exitCode !== 0) {
                refreshError = "Could not read network diagnostics. Retry, or check dms-network-status.";
                return;
            }
            try {
                const next = JSON.parse(stdout);
                if (typeof next !== "object" || next === null || Array.isArray(next) || ![true, false, null].includes(next.connected))
                    throw new Error("Invalid network status");
                networkData = next;
                updatedAt = Date.now();
                clockTime = updatedAt;
                refreshError = next.error || "";
                if (sampleMatches) {
                    trafficHistory = trafficHistory.concat([{
                        "down": Number(next.downloadBytesPerSecond || 0),
                        "up": Number(next.uploadBytesPerSecond || 0)
                    }]).slice(-30);
                }
            } catch (error) {
                refreshError = "Network diagnostics returned invalid data. Retry, or check dms-network-status.";
            }
        }, 100);
    }

    function latency(value, missing = "No reply") {
        return value === null || value === undefined ? missing : Number(value).toFixed(value < 10 ? 1 : 0) + " ms";
    }

    function formatRate(bytes) {
        const value = Number(bytes || 0);
        if (value < 1024) return Math.round(value) + " B/s";
        if (value < 1024 * 1024) return (value / 1024).toFixed(1) + " KiB/s";
        if (value < 1024 * 1024 * 1024) return (value / 1024 / 1024).toFixed(1) + " MiB/s";
        return (value / 1024 / 1024 / 1024).toFixed(1) + " GiB/s";
    }

    function trafficPeak() {
        let peak = 1024;
        for (const sample of trafficHistory) peak = Math.max(peak, sample.down, sample.up);
        return peak;
    }

    function copy(value, label) {
        if (!value) return;
        Quickshell.execDetached(["dms", "cl", "copy", String(value)]);
        ToastService.showInfo(label + " copied");
    }

    Component.onCompleted: refresh()
    Timer { interval: 10000; running: true; repeat: true; onTriggered: root.refresh() }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: root.clockTime = Date.now() }

    component MetricRow: Item {
        required property string label
        required property string value
        property bool copyable: false
        width: parent.width
        height: Math.max(36, metricValue.implicitHeight + Theme.spacingS * 2)
        RowLayout {
            anchors.fill: parent
            spacing: Theme.spacingS
            StyledText {
                text: label
                color: Theme.surfaceVariantText
                font.pixelSize: Theme.fontSizeMedium
                Layout.preferredWidth: 130
            }
            StyledText {
                id: metricValue
                text: value || "—"
                color: Theme.surfaceText
                font.pixelSize: Theme.fontSizeMedium
                horizontalAlignment: Text.AlignRight
                wrapMode: Text.WrapAnywhere
                Layout.fillWidth: true
            }
            DankActionButton {
                visible: copyable && value.length > 0
                iconName: "content_copy"
                buttonSize: 26
                iconSize: 15
                onClicked: root.copy(value, label)
            }
        }
    }

    horizontalBarPill: Component {
        Row {
            spacing: Theme.spacingXS
            DankIcon {
                name: root.connectionIcon
                color: root.linkConnected ? Theme.primary : Theme.widgetIconColor
                size: root.iconSize
                anchors.verticalCenter: parent.verticalCenter
            }
            StyledText {
                text: root.barText
                color: Theme.widgetTextColor
                font.pixelSize: Theme.barTextSize(root.barThickness, root.barConfig?.fontScale, root.barConfig?.maximizeWidgetText)
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
    verticalBarPill: Component {
        DankIcon {
            name: root.connectionIcon
            color: root.linkConnected ? Theme.primary : Theme.widgetIconColor
            size: root.iconSize
        }
    }

    popoutWidth: 540
    popoutHeight: 700
    popoutContent: Component {
        PopoutComponent {
            id: popout
            property bool showDiagnostics: false
            readonly property bool settingsVisible: PopoutService.settingsModal?.visible ?? false
            onSettingsVisibleChanged: { if (settingsVisible && closePopout) closePopout(); }
            headerText: "Network"
            showCloseButton: true
            headerActions: Component {
                Row {
                    spacing: Theme.spacingXS
                    DankActionButton {
                        iconName: NetworkService.wifiEnabled ? "wifi" : "wifi_off"
                        enabled: NetworkService.wifiAvailable && !NetworkService.wifiToggling
                        onClicked: NetworkService.toggleWifiRadio()
                    }
                    DankActionButton {
                        iconName: "refresh"
                        enabled: !NetworkService.isScanning && !root.refreshing
                        onClicked: { NetworkService.scanWifi(); root.refresh(); }
                    }
                }
            }

            Rectangle {
                id: summary
                width: parent.width
                height: summaryColumn.implicitHeight + Theme.spacingM * 2
                radius: Theme.cornerRadius
                color: root.linkConnected ? Theme.primaryPressed : Theme.surfaceLight
                Column {
                    id: summaryColumn
                    x: Theme.spacingM; y: Theme.spacingM
                    width: parent.width - Theme.spacingM * 2
                    spacing: Theme.spacingS
                    RowLayout {
                        width: parent.width
                        spacing: Theme.spacingM
                        DankIcon {
                            name: root.connectionIcon
                            color: root.linkConnected ? Theme.primary : Theme.surfaceVariantText
                            size: 28
                        }
                        Column {
                            Layout.fillWidth: true
                            spacing: Theme.spacingXS
                            StyledText {
                                width: parent.width
                                text: root.connectionTitle
                                font.pixelSize: Theme.fontSizeLarge
                                font.weight: Font.Medium
                                color: Theme.surfaceText
                                elide: Text.ElideRight
                                wrapMode: Text.NoWrap
                            }
                            StyledText {
                                width: parent.width
                                visible: root.linkConnected
                                text: (root.wired ? "Ethernet" : "Wi-Fi") + " · " + root.interfaceName + (root.wired ? "" : " · " + NetworkService.wifiSignalStrength + "% signal")
                                font.pixelSize: Theme.fontSizeSmall
                                color: Theme.surfaceVariantText
                                elide: Text.ElideRight
                                wrapMode: Text.NoWrap
                            }
                        }
                    }
                    Row {
                        width: parent.width
                        spacing: Theme.spacingS
                        DankIcon {
                            name: root.internetWarning ? "info" : root.connectivity === "full" ? "check_circle" : "help_outline"
                            size: 17
                            color: root.internetWarning ? Theme.warning : Theme.surfaceVariantText
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        StyledText {
                            width: parent.width - 25
                            text: root.internetStatus
                            font.pixelSize: Theme.fontSizeMedium
                            color: root.internetWarning ? Theme.warning : Theme.surfaceText
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            StyledText {
                id: statusNote
                width: parent.width
                visible: root.refreshError.length > 0 || (root.updatedAt > 0 && !root.sampleFresh && root.linkConnected)
                text: root.refreshError || "Diagnostics are out of date. Refresh to try again."
                color: Theme.warning
                font.pixelSize: Theme.fontSizeSmall
                wrapMode: Text.WordWrap
                topPadding: Theme.spacingS
            }

            DankTabBar {
                id: tabs
                width: parent.width
                model: [{"text": "Networks"}, {"text": "Connection & diagnostics"}]
                showIcons: false
                tabHeight: 44
                spacing: Theme.spacingS
                currentIndex: popout.showDiagnostics ? 1 : 0
                onTabClicked: index => popout.showDiagnostics = index === 1
            }
            Item { id: gap; width: 1; height: Theme.spacingS }

            NetworkDetails.NetworkDetail {
                width: parent.width
                implicitHeight: height
                height: root.popoutHeight - popout.headerHeight - summary.height - tabs.height - gap.height - (statusNote.visible ? statusNote.height : 0) - 24
                visible: !popout.showDiagnostics
            }

            DankFlickable {
                objectName: "networkDetails"
                width: parent.width
                height: root.popoutHeight - popout.headerHeight - summary.height - tabs.height - gap.height - (statusNote.visible ? statusNote.height : 0) - 24
                contentHeight: details.implicitHeight + Theme.spacingM
                clip: true
                visible: popout.showDiagnostics
                Column {
                    id: details
                    width: parent.width
                    spacing: Theme.spacingS
                    StyledText {
                        width: parent.width
                        text: !root.linkConnected ? "Connect to a network to see its details." : !root.sampleFresh ? "Waiting for current connection details…" : "Connection details"
                        color: Theme.surfaceText
                        font.pixelSize: Theme.fontSizeMedium
                        font.weight: Font.Medium
                        topPadding: Theme.spacingS
                    }
                    Column {
                        width: parent.width
                        visible: root.sampleFresh
                        MetricRow { label: "Address"; value: (root.networkData.addresses || []).join(", "); copyable: true }
                        MetricRow { label: "Gateway"; value: root.networkData.gateway || ""; copyable: true }
                        MetricRow { label: "DNS servers"; value: (root.networkData.dnsServers || []).join(", "); copyable: true }
                        MetricRow { label: "Security"; value: root.networkData.security || (root.wired ? "Wired" : "—") }
                        MetricRow { label: "Link rate"; value: root.networkData.linkRate || "—" }
                        MetricRow { label: "MAC address"; value: root.networkData.mac || ""; copyable: true }
                    }
                    Rectangle { width: parent.width; height: 1; color: Theme.outlineLight }
                    StyledText {
                        text: "Measurements"
                        color: Theme.surfaceText
                        font.pixelSize: Theme.fontSizeMedium
                        font.weight: Font.Medium
                        topPadding: Theme.spacingS
                    }
                    StyledText {
                        width: parent.width
                        text: "A missed ping can mean filtering or packet loss. It does not mean your network is disconnected."
                        color: Theme.surfaceVariantText
                        font.pixelSize: Theme.fontSizeSmall
                        wrapMode: Text.WordWrap
                    }
                    Column {
                        width: parent.width
                        visible: root.sampleFresh
                        MetricRow { label: "Router ping"; value: root.latency(root.networkData.gatewayPingMs) }
                        MetricRow { label: "Public IP ping"; value: root.latency(root.networkData.internetPingMs) }
                        MetricRow { label: "DNS lookup"; value: root.latency(root.networkData.dnsLookupMs, "Unavailable") }
                        MetricRow { label: "Download"; value: root.formatRate(root.networkData.downloadBytesPerSecond) }
                        MetricRow { label: "Upload"; value: root.formatRate(root.networkData.uploadBytesPerSecond) }
                    }
                    Row {
                        spacing: Theme.spacingM
                        visible: root.sampleFresh
                        StyledText { text: "Download"; color: Theme.primary; font.pixelSize: Theme.fontSizeSmall }
                        StyledText { text: "Upload"; color: Theme.surfaceVariantText; font.pixelSize: Theme.fontSizeSmall }
                    }
                    Canvas {
                        id: trafficGraph
                        width: parent.width
                        height: 86
                        visible: root.sampleFresh
                        antialiasing: true
                        onWidthChanged: requestPaint()
                        Connections { target: root; function onTrafficHistoryChanged() { trafficGraph.requestPaint(); } }
                        onPaint: {
                            const ctx = getContext("2d");
                            ctx.clearRect(0, 0, width, height);
                            if (root.trafficHistory.length < 2) return;
                            const peak = root.trafficPeak() * 1.1;
                            for (const series of [{key: "down", color: Theme.primary}, {key: "up", color: Theme.surfaceVariantText}]) {
                                ctx.beginPath(); ctx.lineWidth = 2; ctx.strokeStyle = series.color;
                                for (let i = 0; i < root.trafficHistory.length; i++) {
                                    const x = width * i / 29;
                                    const y = height - 4 - (height - 8) * root.trafficHistory[i][series.key] / peak;
                                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
                                }
                                ctx.stroke();
                            }
                        }
                    }
                    StyledText {
                        width: parent.width
                        text: root.refreshing ? "Measuring…" : root.sampleFresh ? "Updated " + Math.max(0, Math.floor((root.clockTime - root.updatedAt) / 1000)) + " s ago · updates every 10 s" : "Waiting for diagnostics"
                        color: Theme.surfaceVariantText
                        font.pixelSize: Theme.fontSizeSmall
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
