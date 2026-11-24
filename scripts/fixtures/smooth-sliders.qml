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

    // Retargets while moving: every rendered frame stays between the previous
    // displayed position and the current target, so the handle never jumps
    // backwards or leaves its track.
    property int motionStep: 0
    property int motionFrames: 0
    property real motionPrevious: 0
    property real motionTarget: 0
    property real motionStart: 0

    function retargetMotion(value) {
        root.motionTarget = value / 100;
        root.motionFrames = 0;
        root.motionStart = slider.displayedRatio;
        root.motionStep++;
        slider.value = value;
    }

    FrameAnimation {
        id: motion
        onTriggered: {
            const current = slider.displayedRatio;
            const rising = root.motionTarget >= root.motionPrevious;
            const low = rising ? root.motionPrevious : root.motionTarget;
            const high = rising ? root.motionTarget : root.motionPrevious;
            if (!root.check(current >= low - 0.0001 && current <= high + 0.0001, "retarget stays between displayed position and target (step " + root.motionStep + ")")) return;
            root.motionPrevious = current;
            root.motionFrames++;
            const settled = current === slider.ratio;
            switch (root.motionStep) {
            case 0:
                if (root.motionFrames < 2) return;
                // Same-direction repeat: keep moving at the current velocity
                // instead of restarting an easing curve.
                const velocity = slider.displayedVelocity;
                root.retargetMotion(90);
                root.check(current < 0.6 && velocity > 0 && slider.displayedVelocity === velocity, "same-direction repeat keeps velocity");
                return;
            case 1:
                if (root.motionFrames === 1 && !root.check(current > root.motionStart, "motion continues after repeat")) return;
                if (root.motionFrames < 2) return;
                // Close retarget while moving fast: one point above the
                // rounded-up display, where an overshooting tracker reverses.
                root.retargetMotion(Math.min(100, Math.ceil(current * 100) + 1));
                return;
            case 2:
                if (!settled) return;
                root.retargetMotion(90);
                return;
            case 3:
                if (root.motionFrames < 2) return;
                // Reversal: start from rest towards the new target.
                root.retargetMotion(Math.max(0, Math.floor(current * 100) - 10));
                return;
            case 4:
                if (!settled) return;
                motion.stop();
                console.warn("SMOOTH_SLIDER_PASS", JSON.stringify(root.samples));
                Qt.quit();
            }
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
                preferences.reduceMotion = true;
                slider.value = 0;
                preferences.reduceMotion = false;
                root.motionTarget = 0.6;
                root.motionPrevious = 0;
                slider.value = 60;
                motion.start();
                stop();
            }
        }
    }
}
