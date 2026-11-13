import QtQuick
import Quickshell
import qs.Common
import qs.Modals.Clipboard

ShellRoot {
    id: root
    property int phase: 0
    readonly property var scenarios: [
        { width: 550, scale: 1.15, density: 0 },
        { width: 320, scale: 1.15, density: -2 },
        { width: 550, scale: 1.5, density: 0 },
        { width: 320, scale: 1.5, density: 0 }
    ]
    readonly property string multiline: "First line\nSecond line\r\nThird line\u2028Fourth line\u2029Fifth line " + "clipboard preview ".repeat(20)
    readonly property var entries: [
        { id: 1, hash: "short", preview: "Short text", size: 10 },
        { id: 2, hash: "long", preview: multiline, size: multiline.length },
        { id: 3, hash: "url", preview: "https://example.org/" + "verylongpath".repeat(30), size: 500 },
        { id: 4, hash: "image", preview: "Image filename\n" + "very long filename ".repeat(20), size: 100, isImage: true },
        { id: 5, hash: "markup", preview: "<b>literal clipboard markup</b>", size: 30 }
    ]

    QtObject {
        id: testModal
        readonly property var modalFocusScope: null
        function getEntryType(entry) { return entry.isImage ? "image" : entry.size > 200 ? "long_text" : "text"; }
        function getEntryPreview(entry) { return entry.preview; }
    }

    FloatingWindow {
        visible: true
        implicitWidth: 620
        implicitHeight: 520
        Item {
            id: canvas
            anchors.fill: parent
            ListView {
                id: rows
                width: root.scenarios[root.phase].width
                height: parent.height
                model: root.entries
                spacing: Theme.groupedListGap
                delegate: ClipboardEntry {
                    required property int index
                    required property var modelData
                    width: rows.width
                    height: ClipboardConstants.itemHeight
                    entry: modelData
                    itemIndex: index
                    modal: testModal
                    listView: rows
                }
            }
        }
    }

    function labels(item) {
        for (let child of item.children) {
            if (child.children && child.children.length === 2 && child.children[0].text !== undefined
                    && child.children[1].text !== undefined)
                return child.children;
            const found = labels(child);
            if (found) return found;
        }
        return null;
    }

    function check(condition, message) {
        if (condition) return true;
        console.error("CLIPBOARD_HISTORY_TEXT_FAIL", message);
        Qt.exit(1);
        return false;
    }

    function configure() {
        Theme.fontScale = scenarios[phase].scale;
        SettingsData.density = scenarios[phase].density === -2 ? "dense" : "default";
    }
    Component.onCompleted: configure()

    Timer {
        interval: 1500
        running: true
        repeat: true
        onTriggered: {
            rows.forceLayout();
            for (let i = 0; i < root.entries.length; i++) {
                const row = rows.itemAtIndex(i);
                const text = row ? root.labels(row) : null;
                if (!root.check(text && text.length === 2, "actual clipboard row labels exist: " + i)) return;
                for (let label of text) {
                    const pos = label.mapToItem(row, 0, 0);
                    if (!root.check(pos.y >= 0 && pos.y + label.height <= row.height + 1
                            && label.contentHeight <= label.height + 1,
                            "label fits row: phase=" + root.phase + " entry=" + i + " y=" + pos.y
                            + " height=" + label.height + " contentHeight=" + label.contentHeight + " rowHeight=" + row.height)) return;
                }
                if (!root.check(text[0].lineCount === 1, "caption is a single line")) return;
                if (!root.check(text[1].textFormat === Text.PlainText, "clipboard markup is literal")) return;
                if (!root.check(row.entry.preview === root.entries[i].preview, "original preview remains intact")) return;
                if (i === 0 && !root.check(!text[1].truncated, "short text remains readable")) return;
                if ((i === 1 || i === 2) && !root.check(text[1].truncated, "long preview elides: entry=" + i + " phase=" + root.phase + " width=" + text[1].width + " lines=" + text[1].lineCount + " height=" + text[1].height + " implicit=" + text[1].implicitHeight + " type=" + row.entryType + " text=" + text[1].text.substring(0,60))) return;
                if (i === 3 && !root.check(text[0].truncated, "long image caption elides")) return;
            }
            if (root.phase < root.scenarios.length - 1) {
                root.phase++;
                root.configure();
                interval = 250;
                return;
            }
            console.warn("CLIPBOARD_HISTORY_TEXT_PASS: real history rows at 550/320px, font scales 1.15/1.5, normal/dense density; multiline, URLs, image captions, literal markup, short text and unchanged previews");
            running = false;
            const evidence = Quickshell.env("DMS_CLIPBOARD_EVIDENCE");
            if (evidence)
                canvas.grabToImage(result => { result.saveToFile(evidence); Qt.quit(); });
            else
                Qt.quit();
        }
    }
}
