import QtQuick
import Quickshell
import qs.Common
import qs.DCommon.Widgets

ShellRoot {
    id: root
    property int phase: 0
    // Grid sizes span a short Dash card (cramped cells) to a tall one.
    readonly property var scenarios: [
        { width: 300, height: 220, scale: 1.0 },
        { width: 380, height: 260, scale: 1.0 },
        { width: 520, height: 360, scale: 1.0 },
        { width: 300, height: 220, scale: 1.15 },
        { width: 520, height: 420, scale: 1.15 }
    ]
    readonly property var palette: ["#e53935", "#43a047", "#1e88e5", "#fdd835", "#8e24aa", "#00acc1", "#f4511e", "#6d4c41", "#3949ab", "#c0ca33", "#d81b60", "#546e7a"]
    readonly property date anchorDate: new Date(2026, 10, 15, 12)

    function eventCount(date) {
        if (date.getMonth() !== 10)
            return date.getDate() % 5 === 0 ? 4 : 0;
        return [0, 1, 2, 3, 4, 5, 9, 12][date.getDate() % 8];
    }

    function colorsFor(date) {
        return palette.slice(0, eventCount(date));
    }

    FloatingWindow {
        visible: true
        implicitWidth: 560
        implicitHeight: 460
        color: Theme.surfaceContainer

        Item {
            id: canvas
            anchors.fill: parent

            DMonthGrid {
                id: grid
                x: Theme.spacingM
                y: Theme.spacingM
                width: root.scenarios[root.phase].width
                height: root.scenarios[root.phase].height
                displayDate: root.anchorDate
                selectedDate: new Date(2026, 10, 14, 12)
                today: new Date(2026, 10, 14, 12)
                dotColorsFor: date => root.colorsFor(date)
            }
        }
    }

    function texts(item, out) {
        for (let child of item.children) {
            if (child.text !== undefined && child.font !== undefined)
                out.push(child);
            texts(child, out);
        }
        return out;
    }

    function dots(item, out) {
        for (let child of item.children) {
            if (child.text === undefined && child.radius !== undefined && child.width === Theme.spacingXS && child.height === Theme.spacingXS && child.visible)
                out.push(child);
            dots(child, out);
        }
        return out;
    }

    function shown(item, stop) {
        for (let node = item; node && node !== stop; node = node.parent) {
            if (!node.visible || node.opacity === 0)
                return false;
        }
        return true;
    }

    function cells() {
        const out = [];
        for (let child of grid.children) {
            if (child.dayDate !== undefined)
                out.push(child);
        }
        return out;
    }

    function check(condition, message) {
        if (condition)
            return true;
        console.error("CALENDAR_EXTRA_EVENTS_FAIL", message);
        ticker.running = false;
        const evidence = Quickshell.env("DMS_CALENDAR_EVIDENCE");
        if (evidence)
            canvas.grabToImage(result => {
                result.saveToFile(evidence);
                Qt.exit(1);
            });
        else
            Qt.exit(1);
        return false;
    }

    function configure() {
        Theme.fontScale = scenarios[phase].scale;
    }
    Component.onCompleted: configure()

    Timer {
        id: ticker
        interval: 1500
        running: true
        repeat: true
        onTriggered: {
            const all = root.cells();
            if (!root.check(all.length === 42, "actual month grid cells exist: " + all.length))
                return;
            let labelsShown = 0;
            for (let cell of all) {
                const count = root.eventCount(cell.dayDate);
                const where = "phase=" + root.phase + " day=" + cell.dayDate.getDate() + " events=" + count + " cell=" + cell.width.toFixed(1) + "x" + cell.height.toFixed(1);
                const labels = root.texts(cell, []);
                const day = labels.find(label => label.text === String(cell.dayDate.getDate()));
                if (!root.check(day, "day number exists: " + where))
                    return;
                const dayBox = day.mapToItem(cell, 0, 0);
                const dayTop = dayBox.y + (day.height - day.contentHeight) / 2;
                const dayBottom = dayTop + day.contentHeight;
                const visibleDots = root.dots(cell, []).filter(dot => root.shown(dot, cell));
                if (!root.check(visibleDots.length === Math.min(count, grid.maxDots), "dot count: " + where + " shown=" + visibleDots.length))
                    return;
                for (let dot of visibleDots) {
                    const box = dot.mapToItem(cell, 0, 0);
                    if (!root.check(box.y >= dayBottom && box.y + dot.height <= cell.height && box.x >= 0 && box.x + dot.width <= cell.width, "dot clear of number and inside cell: " + where + " dotY=" + box.y.toFixed(1) + " dayBottom=" + dayBottom.toFixed(1)))
                        return;
                }
                const extra = labels.filter(label => label.text.startsWith("+") && root.shown(label, cell));
                if (count <= grid.maxDots) {
                    if (!root.check(extra.length === 0, "no extra label at or below the dot limit: " + where))
                        return;
                    continue;
                }
                for (let label of extra) {
                    const box = label.mapToItem(cell, 0, 0);
                    const top = box.y + (label.height - label.contentHeight) / 2;
                    const bottom = top + label.contentHeight;
                    if (!root.check(label.text === "+" + (count - grid.maxDots), "extra label counts hidden events: " + where + " text=" + label.text))
                        return;
                    if (!root.check(top >= dayBottom - 0.5 && bottom <= cell.height + 0.5 && box.x >= 0 && box.x + label.contentWidth <= cell.width + 0.5, "extra label clear of number and inside cell: " + where + " labelTop=" + top.toFixed(1) + " labelBottom=" + bottom.toFixed(1) + " dayBottom=" + dayBottom.toFixed(1)))
                        return;
                    labelsShown++;
                }
            }
            if (root.phase === 2 && !root.check(labelsShown > 0, "roomy cells still show the +N count"))
                return;
            console.warn("CALENDAR_EXTRA_EVENTS_INFO phase=" + root.phase + " cell=" + all[0].width.toFixed(1) + "x" + all[0].height.toFixed(1) + " extraLabels=" + labelsShown);
            if (root.phase < root.scenarios.length - 1) {
                root.phase++;
                root.configure();
                interval = 250;
                return;
            }
            console.warn("CALENDAR_EXTRA_EVENTS_PASS: actual month grid at 300x220 to 520x420, font scales 1.0/1.15, 0-12 events per day; dots and +N stay clear of the day number and inside the cell");
            running = false;
            const evidence = Quickshell.env("DMS_CALENDAR_EVIDENCE");
            if (evidence) {
                root.phase = Number(Quickshell.env("DMS_CALENDAR_EVIDENCE_PHASE") || 0);
                root.configure();
                canvas.grabToImage(result => {
                    result.saveToFile(evidence);
                    Qt.quit();
                });
            } else {
                Qt.quit();
            }
        }
    }
}
