import QtQuick
import Quickshell
import qs.Common
import qs.Services
import qs.Widgets
import qs.Modules.Plugins

PluginComponent {
    id: root
    Ref { service: DMSNetworkService }
    readonly property bool connected: (DMSNetworkService.activeNames || []).includes("TU Dortmund Studierende")
    property bool busy: false
    property string lastError: ""
    popoutWidth: 360
    popoutHeight: lastError ? 250 : 190

    function run(action) {
        if (busy)
            return;
        busy = true;
        lastError = "";
        Proc.runCommand("tuVpn.action", [(Quickshell.env("HOME") || "") + "/.local/bin/tu-vpn", action], (stdout, exitCode) => {
            busy = false;
            DMSNetworkService.getState();
            if (exitCode !== 0) {
                lastError = "VPN " + action + " failed. Check your login wallet and university account.";
                ToastService.showError("TU Dortmund VPN", lastError);
            }
        }, 100);
    }

    pillRightClickAction: () => root.run(root.connected ? "disconnect" : "connect")
    horizontalBarPill: Component {
        DankIcon {
            name: root.connected ? "vpn_lock" : "vpn_key_off"
            color: root.connected ? Theme.primary : Theme.widgetIconColor
            size: root.iconSize
            opacity: root.busy ? 0.5 : 1
        }
    }
    verticalBarPill: horizontalBarPill
    popoutContent: Component {
        PopoutComponent {
            headerText: "TU Dortmund VPN"
            detailsText: root.busy ? "Working…" : (root.connected ? "Connected" : "Disconnected")
            showCloseButton: true
            Column {
                width: parent.width
                spacing: Theme.spacingM
                StyledText {
                    visible: root.lastError.length > 0
                    width: parent.width
                    text: root.lastError
                    wrapMode: Text.WordWrap
                    color: Theme.error
                }
                DankButton {
                    text: root.connected ? "Disconnect" : "Connect"
                    iconName: root.connected ? "link_off" : "vpn_key"
                    enabled: !root.busy
                    onClicked: root.run(root.connected ? "disconnect" : "connect")
                }
            }
        }
    }
}
