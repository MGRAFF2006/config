import QtQuick
import Quickshell
import qs.Common
import qs.Modals.DLauncherV2.Components

ShellRoot {
    id: root
    property int phase: 0
    Component.onCompleted: Theme.fontScale = 1.15
    readonly property string fullTitle: "[Recreate Slides Figures as SVGs](t3-context://v1/thread/thread_1234) a long clipboard entry that must fit its result row"
    readonly property string multilineTitle: "A multiline clipboard entry\nsecond line\r\nthird line https://example.org/a/very/long/url/without/spaces"

    FloatingWindow {
        id: window
        visible: true
        implicitWidth: 620
        implicitHeight: 270

        Column {
            id: rows
            width: root.phase === 0 ? parent.width : 320
            LauncherRow {
                id: highlighted
                item: ({ type: "clipboard", name: root.fullTitle, subtitle: "Text - Shift+Enter to paste a very long subtitle that must also fit the row",
                    _hName: "[Recreate Slides Figures as SVGs](<b>t3</b>-context://v1/thread/thread_1234) a long clipboard entry that must fit its result row",
                    _hSub: "Text - Shift+Enter to <b>paste</b> a very long subtitle that must also fit the row", _hRich: true,
                    iconType: "material", icon: "content_paste", data: { content: root.fullTitle } })
            }
            LauncherRow {
                id: multiline
                item: ({ type: "clipboard", name: root.multilineTitle, subtitle: "Text - Shift+Enter to paste", _hRich: false,
                    iconType: "material", icon: "content_paste", data: { content: root.multilineTitle } })
            }
            LauncherRow {
                id: shortRow
                item: ({ type: "app", name: "T3 Code Nightly", subtitle: "T3 Code nightly desktop build", iconType: "material", icon: "apps" })
            }
            LauncherRow {
                id: markupRow
                item: ({ type: "dmenu", name: "Large", subtitle: "", _hRich: true,
                    _hName: '<span style="font-size:30px; color:red">Large</span>', iconType: "material", icon: "apps" })
            }
        }
    }

    function check(condition, message) {
        if (!condition) {
            console.error("LAUNCHER_TEXT_FAIL", message);
            Qt.exit(1);
        }
        return condition;
    }

    function textItems(row) {
        // Inspect the actual row's two labels, without exporting test-only API.
        for (let child of row.children) {
            if (child.children && child.children.length >= 2 && child.children[0].text !== undefined
                    && child.children[0].font !== undefined) {
                const labels = [];
                for (let label of child.children) {
                    if (label.text !== undefined && label.font !== undefined && label.mapToItem !== undefined)
                        labels.push(label);
                }
                if (labels.length === 2)
                    return labels;
            }
        }
        return [];
    }

    function verifyRow(row, shouldTruncate) {
        const labels = textItems(row);
        if (!check(labels.length === 2, "actual row title and subtitle found")) return false;
        for (let label of labels) {
            const top = label.mapToItem(row, 0, 0).y;
            if (!check(label.lineCount === 1 && top >= 0 && top + label.height <= row.height,
                    "each label stays within its single row at width " + row.width)) return false;
        }
        return check(labels[0].truncated === shouldTruncate, "long titles elide and short titles remain intact");
    }

    Timer {
        interval: 1500
        running: true
        repeat: true
        onTriggered: {
            if (!root.verifyRow(highlighted, true) || !root.verifyRow(multiline, true)
                    || !root.verifyRow(shortRow, false)) return;
            if (!root.check(highlighted.item.data.content === root.fullTitle && multiline.item.name === root.multilineTitle
                    && multiline.item.data.content === root.multilineTitle, "full clipboard payload and names stay unchanged")) return;
            if (root.phase++ === 0) {
                interval = 250;
                return;
            }
            if (!root.check(root.textItems(highlighted)[1].truncated, "highlighted subtitle also elides on a narrow launcher")) return;
            const markupTitle = root.textItems(markupRow)[0];
            if (!root.check(markupTitle.textFormat === Text.RichText && markupTitle.contentHeight >= 30,
                    "explicit dmenu rich markup preserves its CSS font size")) return;
            console.warn("LAUNCHER_TEXT_PASS: highlighted and plain long titles, multiline clipboard payloads, subtitles, short titles at 620px and 320px, font scale 1.15");
            const evidence = Quickshell.env("DMS_LAUNCHER_EVIDENCE");
            if (evidence) {
                rows.grabToImage(result => { result.saveToFile(evidence); Qt.quit(); });
            } else {
                Qt.quit();
            }
        }
    }
}
