import QtQuick
import Quickshell
import qs.Common
import qs.Services
import qs.Widgets
import qs.Modules.Plugins

PluginComponent {
    id: root

    property var networkData: ({ "connected": false })
    property var trafficHistory: []
    property bool refreshing: false
    readonly property string statusCommand: (Quickshell.env("HOME") || "") + "/.local/bin/dms-network-status"

    function refresh() {
        refreshing = true;
        const screenKey = parentScreen?.name || "default";
        Proc.runCommand("networkDiagnostics.status." + screenKey, [statusCommand], (stdout, exitCode) => {
            refreshing = false;
            if (exitCode !== 0)
                return;
            try {
                const next = JSON.parse(stdout);
                networkData = next;
                trafficHistory = trafficHistory.concat([{
                    "down": Number(next.downloadBytesPerSecond || 0),
                    "up": Number(next.uploadBytesPerSecond || 0)
                }]).slice(-60);
            } catch (error) {
                console.warn("NetworkDiagnostics: invalid status JSON:", error);
            }
        }, 100);
    }

    function latency(value) {
        return value === null || value === undefined ? "Offline" : Number(value).toFixed(value < 10 ? 1 : 0) + " ms";
    }

    function formatRate(bytes) {
        const value = Number(bytes || 0);
        if (value < 1024)
            return Math.round(value) + " B/s";
        if (value < 1024 * 1024)
            return (value / 1024).toFixed(1) + " KiB/s";
        if (value < 1024 * 1024 * 1024)
            return (value / 1024 / 1024).toFixed(1) + " MiB/s";
        return (value / 1024 / 1024 / 1024).toFixed(1) + " GiB/s";
    }

    function trafficPeak() {
        let peak = 1024;
        for (const sample of trafficHistory)
            peak = Math.max(peak, Number(sample.down || 0), Number(sample.up || 0));
        return peak;
    }

    function copy(value, label) {
        if (!value)
            return;
        Quickshell.execDetached(["dms", "cl", "copy", String(value)]);
        ToastService.showInfo(label + " copied");
    }

    Component.onCompleted: refresh()

    Timer {
        interval: 5000
        running: true
        repeat: true
        onTriggered: root.refresh()
    }

    component MetricRow: Item {
        required property string label
        required property string value
        property string icon: ""
        property bool copyable: false

        width: parent ? parent.width : 0
        height: 34

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.spacingS

            DankIcon {
                visible: icon.length > 0
                name: icon
                size: 17
                color: Theme.surfaceVariantText
                anchors.verticalCenter: parent.verticalCenter
            }

            StyledText {
                text: label
                color: Theme.surfaceVariantText
                font.pixelSize: Theme.fontSizeMedium
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            spacing: Theme.spacingXS

            StyledText {
                width: Math.min(implicitWidth, 310)
                text: value || "—"
                color: Theme.surfaceText
                font.pixelSize: Theme.fontSizeMedium
                font.weight: Font.Medium
                elide: Text.ElideMiddle
                horizontalAlignment: Text.AlignRight
                anchors.verticalCenter: parent.verticalCenter
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
                name: !root.networkData.connected ? "wifi_off" : (root.networkData.type === "ethernet" ? "lan" : "wifi")
                color: root.networkData.connected ? Theme.primary : Theme.error
                size: root.iconSize
                anchors.verticalCenter: parent.verticalCenter
            }

            StyledText {
                text: root.latency(root.networkData.internetPingMs)
                color: root.networkData.internetPingMs === null ? Theme.error : Theme.widgetTextColor
                font.pixelSize: Theme.barTextSize(root.barThickness, root.barConfig?.fontScale, root.barConfig?.maximizeWidgetText)
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }

    verticalBarPill: Component {
        Column {
            spacing: Theme.spacingXXS

            DankIcon {
                name: !root.networkData.connected ? "wifi_off" : (root.networkData.type === "ethernet" ? "lan" : "wifi")
                color: root.networkData.connected ? Theme.primary : Theme.error
                size: root.iconSize
                anchors.horizontalCenter: parent.horizontalCenter
            }

            StyledText {
                text: root.networkData.internetPingMs === null ? "—" : Math.round(root.networkData.internetPingMs)
                color: Theme.widgetTextColor
                font.pixelSize: Theme.fontSizeSmall
                anchors.horizontalCenter: parent.horizontalCenter
            }
        }
    }

    popoutContent: Component {
        PopoutComponent {
            id: popout

            headerText: root.networkData.ssid || root.networkData.connection || "Network"
            detailsText: root.networkData.connected ? (root.networkData.interface + " • " + (root.networkData.security || root.networkData.type)) : "No active connection"
            showCloseButton: true

            Item {
                width: parent.width
                height: root.popoutHeight - popout.headerHeight - popout.detailsHeight

                DankFlickable {
                    anchors.fill: parent
                    contentHeight: detailColumn.implicitHeight + Theme.spacingM
                    clip: true

                    Column {
                        id: detailColumn
                        width: parent.width
                        spacing: Theme.spacingM
                        topPadding: Theme.spacingS

                        StyledRect {
                            width: parent.width
                            implicitHeight: connectionColumn.implicitHeight + Theme.spacingM * 2
                            radius: Theme.cornerRadius
                            color: Theme.surfaceContainerHigh

                            Column {
                                id: connectionColumn
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: Theme.spacingM

                                StyledText {
                                    text: "Connection"
                                    color: Theme.surfaceText
                                    font.pixelSize: Theme.fontSizeLarge
                                    font.weight: Font.Medium
                                }

                                MetricRow {
                                    label: "Password"
                                    value: root.networkData.password || (root.networkData.type === "wifi" ? "Not stored" : "Not applicable")
                                    icon: "key"
                                    copyable: Boolean(root.networkData.password)
                                }
                                MetricRow {
                                    label: "Signal"
                                    value: root.networkData.type === "wifi" ? ((root.networkData.signal || 0) + "% • " + (root.networkData.linkRate || "unknown rate")) : "Wired"
                                    icon: "signal_cellular_alt"
                                }
                                MetricRow {
                                    label: "Address"
                                    value: (root.networkData.addresses || []).join(", ")
                                    icon: "language"
                                    copyable: true
                                }
                                MetricRow {
                                    label: "Gateway"
                                    value: root.networkData.gateway || ""
                                    icon: "router"
                                    copyable: true
                                }
                                MetricRow {
                                    label: "DNS"
                                    value: (root.networkData.dnsServers || []).join(", ")
                                    icon: "dns"
                                    copyable: true
                                }
                                MetricRow {
                                    label: "MAC"
                                    value: root.networkData.mac || ""
                                    icon: "fingerprint"
                                    copyable: true
                                }
                            }
                        }

                        StyledRect {
                            width: parent.width
                            implicitHeight: diagnosticsColumn.implicitHeight + Theme.spacingM * 2
                            radius: Theme.cornerRadius
                            color: Theme.surfaceContainerHigh

                            Column {
                                id: diagnosticsColumn
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: Theme.spacingM

                                StyledText {
                                    text: "Diagnostics"
                                    color: Theme.surfaceText
                                    font.pixelSize: Theme.fontSizeLarge
                                    font.weight: Font.Medium
                                }

                                MetricRow {
                                    label: "Router ping"
                                    value: root.latency(root.networkData.gatewayPingMs)
                                    icon: "router"
                                }
                                MetricRow {
                                    label: "Internet ping"
                                    value: root.latency(root.networkData.internetPingMs)
                                    icon: "public"
                                }
                                MetricRow {
                                    label: "DNS lookup"
                                    value: root.latency(root.networkData.dnsLookupMs)
                                    icon: "dns"
                                }
                                MetricRow {
                                    label: "Traffic"
                                    value: "↓ " + root.formatRate(root.networkData.downloadBytesPerSecond) + "   ↑ " + root.formatRate(root.networkData.uploadBytesPerSecond)
                                    icon: "swap_vert"
                                }
                            }
                        }

                        StyledRect {
                            width: parent.width
                            implicitHeight: trafficColumn.implicitHeight + Theme.spacingM * 2
                            radius: Theme.cornerRadius
                            color: Theme.surfaceContainerHigh

                            Column {
                                id: trafficColumn
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.margins: Theme.spacingM
                                spacing: Theme.spacingS

                                Row {
                                    width: parent.width

                                    StyledText {
                                        text: "Traffic history"
                                        color: Theme.surfaceText
                                        font.pixelSize: Theme.fontSizeLarge
                                        font.weight: Font.Medium
                                    }

                                    Item {
                                        width: parent.width - parent.children[0].width - liveTraffic.width
                                        height: 1
                                    }

                                    StyledText {
                                        id: liveTraffic
                                        text: "↓ " + root.formatRate(root.networkData.downloadBytesPerSecond) + "  ↑ " + root.formatRate(root.networkData.uploadBytesPerSecond)
                                        color: Theme.surfaceVariantText
                                        font.pixelSize: Theme.fontSizeSmall
                                    }
                                }

                                Item {
                                    width: parent.width
                                    height: 126

                                    Canvas {
                                        id: trafficGraph
                                        anchors.fill: parent
                                        antialiasing: true

                                        onWidthChanged: requestPaint()
                                        onHeightChanged: requestPaint()

                                        Connections {
                                            target: root
                                            function onTrafficHistoryChanged() {
                                                trafficGraph.requestPaint();
                                            }
                                        }

                                        onPaint: {
                                            const ctx = getContext("2d");
                                            ctx.clearRect(0, 0, width, height);
                                            const samples = root.trafficHistory;
                                            const left = 2;
                                            const top = 4;
                                            const graphWidth = Math.max(1, width - 4);
                                            const graphHeight = Math.max(1, height - 8);

                                            ctx.lineWidth = 1;
                                            ctx.strokeStyle = Theme.withAlpha(Theme.outline, 0.35);
                                            for (let line = 0; line <= 3; line++) {
                                                const y = top + graphHeight * line / 3;
                                                ctx.beginPath();
                                                ctx.moveTo(left, y);
                                                ctx.lineTo(left + graphWidth, y);
                                                ctx.stroke();
                                            }
                                            if (samples.length < 2)
                                                return;

                                            const peak = root.trafficPeak() * 1.1;
                                            function drawSeries(key, color) {
                                                ctx.beginPath();
                                                ctx.lineWidth = 2;
                                                ctx.lineJoin = "round";
                                                ctx.lineCap = "round";
                                                ctx.strokeStyle = color;
                                                for (let index = 0; index < samples.length; index++) {
                                                    const x = left + graphWidth * index / 59;
                                                    const value = Math.max(0, Number(samples[index][key] || 0));
                                                    const y = top + graphHeight - graphHeight * value / peak;
                                                    if (index === 0)
                                                        ctx.moveTo(x, y);
                                                    else
                                                        ctx.lineTo(x, y);
                                                }
                                                ctx.stroke();
                                            }
                                            drawSeries("down", Theme.primary);
                                            drawSeries("up", Theme.error);
                                        }
                                    }
                                }

                                Row {
                                    width: parent.width
                                    spacing: Theme.spacingM

                                    Row {
                                        spacing: Theme.spacingXS
                                        Rectangle {
                                            width: 9
                                            height: 9
                                            radius: 5
                                            color: Theme.primary
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                        StyledText {
                                            text: "Download"
                                            color: Theme.surfaceVariantText
                                            font.pixelSize: Theme.fontSizeSmall
                                        }
                                    }

                                    Row {
                                        spacing: Theme.spacingXS
                                        Rectangle {
                                            width: 9
                                            height: 9
                                            radius: 5
                                            color: Theme.error
                                            anchors.verticalCenter: parent.verticalCenter
                                        }
                                        StyledText {
                                            text: "Upload"
                                            color: Theme.surfaceVariantText
                                            font.pixelSize: Theme.fontSizeSmall
                                        }
                                    }

                                    Item {
                                        width: parent.width - parent.children[0].width - parent.children[1].width - peakLabel.width - Theme.spacingM * 3
                                        height: 1
                                    }

                                    StyledText {
                                        id: peakLabel
                                        text: "Scale " + root.formatRate(root.trafficPeak())
                                        color: Theme.surfaceVariantText
                                        font.pixelSize: Theme.fontSizeSmall
                                    }
                                }
                            }
                        }

                        StyledText {
                            width: parent.width
                            text: root.refreshing ? "Refreshing…" : "Updates every 5 seconds"
                            color: Theme.surfaceVariantText
                            font.pixelSize: Theme.fontSizeSmall
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }
        }
    }

    popoutWidth: 540
    popoutHeight: 760
}
