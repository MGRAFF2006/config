import QtQuick
import QtQuick.Layouts
import Quickshell
import qs.Common
import qs.Services
import qs.Widgets
import qs.Modules.Plugins

PluginComponent {
    id: root

    Ref { service: DMSNetworkService }

    readonly property string tuProfile: "TU Dortmund Studierende"
    readonly property bool connected: (DMSNetworkService.activeNames || []).includes(tuProfile)
    property bool busy: false
    property string pendingAction: ""
    property string lastError: ""
    popoutWidth: 480
    popoutHeight: 430

    function run(action) {
        if (busy) return;
        busy = true;
        pendingAction = action;
        lastError = "";
        Proc.runCommand("tuVpn.action", [(Quickshell.env("HOME") || "") + "/.local/bin/tu-vpn", action], (stdout, exitCode) => {
            busy = false;
            DMSNetworkService.getState();
            if (exitCode !== 0) {
                lastError = "VPN " + action + " failed. Unlock your login wallet and check your university login, then retry.";
                ToastService.showError("TU Dortmund VPN", lastError);
            }
        }, 100);
    }

    function toggleProfile(profile) {
        // DMS's generic OpenConnect path cannot supply the TU server's cookie.
        if (profile.name === tuProfile)
            run(connected ? "disconnect" : "connect");
        else
            DMSNetworkService.toggle(profile.uuid);
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
            id: popout
            property string expandedUuid: ""
            headerText: "VPN"
            detailsText: root.busy ? (root.pendingAction === "disconnect" ? "Disconnecting…" : "Connecting to TU Dortmund…") : DMSNetworkService.connected ? "Active: " + DMSNetworkService.activeNames.join(", ") : "No active VPN"
            showCloseButton: true
            headerActions: Component {
                DankActionButton {
                    iconName: "settings"
                    onClicked: {
                        if (popout.closePopout) popout.closePopout();
                        PopoutService.openSettingsWithTab("network_vpn");
                    }
                }
            }

            DankFlickable {
                width: parent.width
                height: root.popoutHeight - popout.headerHeight - popout.detailsHeight - Theme.spacingM
                contentHeight: profilesColumn.implicitHeight
                clip: true

                Column {
                    id: profilesColumn
                    width: parent.width
                    spacing: Theme.spacingM

                    StyledText {
                        width: parent.width
                        visible: text.length > 0
                        text: root.lastError || DMSNetworkService.vpnError
                        color: Theme.error
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: DMSNetworkService.profiles
                        delegate: Rectangle {
                            id: profileCard
                            required property var modelData
                            readonly property bool isTu: modelData.name === root.tuProfile
                            readonly property bool active: DMSNetworkService.vpnStateForUuid(modelData.uuid) === "activated"
                            readonly property bool working: isTu ? root.busy : DMSNetworkService.isVpnConnectingUuid(modelData.uuid)
                            readonly property bool expanded: popout.expandedUuid === modelData.uuid
                            width: profilesColumn.width
                            height: profileContent.implicitHeight + Theme.spacingM * 2
                            radius: Theme.cornerRadius
                            color: active ? Theme.primaryPressed : Theme.surfaceLight
                            border.width: active ? 2 : 1
                            border.color: active ? Theme.primary : Theme.outlineLight

                            Column {
                                id: profileContent
                                x: Theme.spacingM
                                y: Theme.spacingM
                                width: parent.width - Theme.spacingM * 2
                                spacing: Theme.spacingM

                                RowLayout {
                                    width: parent.width
                                    spacing: Theme.spacingS
                                    DankIcon {
                                        name: profileCard.active ? "vpn_lock" : "vpn_key_off"
                                        color: profileCard.active ? Theme.primary : Theme.surfaceText
                                        size: 24
                                    }
                                    Column {
                                        Layout.fillWidth: true
                                        StyledText {
                                            width: parent.width
                                            text: profileCard.modelData.name
                                            color: profileCard.active ? Theme.primary : Theme.surfaceText
                                            font.pixelSize: Theme.fontSizeMedium
                                            font.weight: Font.Medium
                                            elide: Text.ElideRight
                                        }
                                        StyledText {
                                            text: profileCard.working ? "Working…" : profileCard.active ? "Connected" : "Disconnected"
                                            color: profileCard.working ? Theme.warning : Theme.surfaceVariantText
                                            font.pixelSize: Theme.fontSizeSmall
                                        }
                                    }
                                    DankActionButton {
                                        iconName: profileCard.expanded ? "expand_less" : "expand_more"
                                        onClicked: popout.expandedUuid = profileCard.expanded ? "" : profileCard.modelData.uuid
                                    }
                                }

                                Column {
                                    width: parent.width
                                    spacing: Theme.spacingS
                                    visible: profileCard.expanded
                                    StyledText {
                                        width: parent.width
                                        text: profileCard.isTu ? "stud.vpn.tu-dortmund.de" : VPNService.getVpnTypeFromProfile(profileCard.modelData)
                                        color: Theme.surfaceText
                                        wrapMode: Text.WrapAnywhere
                                    }
                                    StyledText {
                                        width: parent.width
                                        text: profileCard.isTu ? "University login saved in your login wallet. Reconnect without entering it again." : "Manage this profile in VPN settings."
                                        color: Theme.surfaceVariantText
                                        font.pixelSize: Theme.fontSizeSmall
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                DankButton {
                                    width: parent.width
                                    text: profileCard.working ? "Working…" : profileCard.active ? "Disconnect" : "Connect"
                                    iconName: profileCard.active ? "link_off" : "vpn_key"
                                    enabled: !root.busy && !DMSNetworkService.isBusy
                                    onClicked: root.toggleProfile(profileCard.modelData)
                                }
                            }
                        }
                    }

                    StyledText {
                        visible: DMSNetworkService.profiles.length === 0
                        width: parent.width
                        text: "No VPN profiles. Open VPN settings to import one."
                        color: Theme.surfaceVariantText
                        wrapMode: Text.WordWrap
                    }

                    DankButton {
                        width: parent.width
                        text: "Manage & import profiles"
                        iconName: "settings"
                        backgroundColor: Theme.surfaceLight
                        textColor: Theme.surfaceText
                        onClicked: {
                            if (popout.closePopout) popout.closePopout();
                            PopoutService.openSettingsWithTab("network_vpn");
                        }
                    }
                }
            }
        }
    }
}
