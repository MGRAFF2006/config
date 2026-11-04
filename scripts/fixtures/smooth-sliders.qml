import QtQuick
import Quickshell
import qs.DCommon.Widgets
import qs.DCommon.Common

ShellRoot {
    id: root
    property int commits: 0
    property int phase: 0
    property var samples: []
    property int repeats: 0
    property int movingFrames: 0
    property real previousRatio: 0.2

    QtObject { id: preferences; property bool reduceMotion: false }
    Component.onCompleted: Style.settings = preferences

    FloatingWindow {
        id: window
        visible: true
        implicitWidth: 420
        implicitHeight: 100
        DSlider {
            id: slider
            anchors.centerIn: parent
            width: 360
            value: 20
            onSliderValueChanged: root.commits++
        }
    }

    function check(condition, message) {
        if (!condition) {
            console.error("SMOOTH_SLIDER_FAIL", message, slider.value, slider.ratio, slider.displayedRatio, root.commits);
            Qt.exit(1);
            return false;
        }
        return true;
    }

    Timer {
        id: heldKey
        interval: 40
        repeat: true
        onTriggered: {
            root.repeats++;
            slider.value = 20 + root.repeats * 5;
            if (!root.check(slider.value === 20 + root.repeats * 5 && root.commits === 1, "held key updates model without hardware feedback")) return;
            if (root.repeats === 12)
                stop();
        }
    }

    FrameAnimation {
        running: heldKey.running
        onTriggered: {
            const current = slider.displayedRatio;
            if (!root.check(current >= root.previousRatio - 0.001 && current <= slider.ratio + 0.001, "held key stays monotonic and bounded")) return;
            if (current > root.previousRatio + 0.0001)
                root.movingFrames++;
            root.previousRatio = current;
        }
    }

    Timer {
        id: steps
        interval: 180
        running: true
        repeat: true
        onTriggered: {
            switch (root.phase++) {
            case 0:
                slider.value = 80;
                if (!root.check(slider.value === 80 && Math.abs(slider.ratio - 0.8) < 0.001 && root.commits === 0, "immediate model value and no hardware commit")) return;
                interval = 45;
                break;
            case 1:
                root.samples.push(slider.displayedRatio);
                if (!root.check(slider.displayedRatio > 0.2 && slider.displayedRatio < 0.8, "intermediate progress")) return;
                interval = 150;
                break;
            case 2:
                if (!root.check(Math.abs(slider.displayedRatio - 0.8) < 0.001, "settled progress")) return;
                slider.value = 20;
                interval = 35;
                break;
            case 3:
                slider.value = 70;
                interval = 35;
                break;
            case 4:
                root.samples.push(slider.displayedRatio);
                if (!root.check(slider.displayedRatio >= 0.2 && slider.displayedRatio <= 0.8, "bounded rapid retarget")) return;
                slider.value = 30;
                interval = 150;
                break;
            case 5:
                if (!root.check(Math.abs(slider.displayedRatio - 0.3) < 0.001, "rapid retarget settles")) return;
                slider.isDragging = true;
                slider.value = 75;
                if (!root.check(Math.abs(slider.displayedRatio - 0.75) < 0.001, "drag snaps without lag")) return;
                slider.isDragging = false;
                preferences.reduceMotion = true;
                slider.value = 40;
                if (!root.check(Math.abs(slider.displayedRatio - 0.4) < 0.001, "reduced motion snaps")) return;
                slider.commit(60);
                if (!root.check(root.commits === 1 && slider.value === 60, "user commit stays immediate")) return;
                slider.value = 20;
                preferences.reduceMotion = false;
                heldKey.start();
                interval = 900;
                break;
            case 6:
                if (!root.check(root.repeats === 12 && root.movingFrames > root.repeats && Math.abs(slider.displayedRatio - 0.8) < 0.001, "held sequence renders between repeats and settles after release")) return;
                console.warn("SMOOTH_SLIDER_PASS", JSON.stringify(root.samples));
                Qt.quit();
            }
        }
    }
}
