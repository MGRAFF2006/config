import QtQuick
import QtTest
import Quickshell.Services.Pam
import qs.Common
import qs.Services
import "PRODUCTION" as Production

TestCase {
    name: "HowdyLock"
    when: true

    Production.Pam { id: lockPam }
    property alias pam: lockPam

    // Host for the pinned DMS password field: the check script pastes its key
    // handling verbatim, so key presses take the real authBusy guard.
    QtObject {
        id: root
        property bool demoMode: false
        property bool unlocking: false
        readonly property var pam: lockPam
        readonly property var log: ({ debug: function() {} })
        readonly property string passwordBuffer: lockPam.buffer
        readonly property QtObject lockHost: QtObject {
            function passwordEdited(text) { lockPam.buffer = text; }
            function setInputRevealed(revealed) {}
        }
        function securityKeyShortcutMatches(event) { return false; }
        function canStartSecurityKeyUnlock() { return false; }
        function triggerSecurityKeyUnlock() {}
    }
    QtObject { id: keyboardController; property bool isKeyboardActive: false; function hide() {} }
    QtObject { id: passwordBox; property bool showPassword: false }
    QtObject { id: passwordDisplay; function selectAll() {} function deselect() {} }
    Item {
        id: passwordField
        // PINNED_PASSWORD_FIELD
    }

    function press(key, text) {
        const event = { key: key, text: text || "", modifiers: Qt.NoModifier, accepted: false };
        passwordField.handleKey(event);
        return event.accepted;
    }

    function type(text) {
        for (const character of text)
            verify(press(0, character), "key press was not consumed by the password field");
    }

    function watchdog() {
        for (let i = 0; i < pam.data.length; ++i) {
            const object = pam.data[i];
            if (object.interval === 15000 && typeof object.restart === "function")
                return object;
        }
        fail("Production PAM watchdog not found");
    }

    function init() {
        pam.lockSecured = false;
        pam.resetAuthFlows();
        pam.buffer = "";
        pam.responseSubmitted = false;
        pam.awaitingUserInput = false;
        pam.state = "";
        pam.passwd.startCount = 0;
        pam.passwd.abortCount = 0;
        pam.passwd.responses = [];
        SettingsData.lockPamExternallyManaged = true;
        SettingsData.lockPamPath = "/etc/pam.d/dankshell";
        SettingsData.pamFilePresent = true;
        SettingsData.pamText = passwordFirst;
        AdminPolicy.disableCustomLockPam = false;
        SessionService.preparingForSleep = false;
        SessionService.sleepRequested = false;
        IdleService.monitorsOff = false;
        wait(1);
    }

    readonly property string passwordFirst: "auth [success=2 default=ignore] pam_unix.so try_first_pass nullok\nauth [success=1 default=ignore] pam_howdy.so\nauth requisite pam_deny.so\n"

    function cleanup() {
        pam.lockSecured = false;
        pam.resetAuthFlows();
        wait(1);
    }

    function unlockSpy() {
        const spy = Qt.createQmlObject('import QtTest; SignalSpy {}', this);
        spy.target = pam;
        spy.signalName = "unlockRequested";
        return spy;
    }

    // Lock-screen key/click input reaches Pam.retryFprintOnActivity().
    function startAutomatic() {
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        tryCompare(pam.passwd, "startCount", 1);
        verify(pam.passwd.active);
    }

    function test_auto_start_uses_managed_stack() {
        startAutomatic();
        compare(pam.passwd.config, "dankshell");
        compare(pam.passwd.configDirectory, "/etc/pam.d");
        verify(!pam.authBusy, "The password field keeps taking keys during the face attempt");
        verify(watchdog().running, "Automatic authentication needs stall recovery");
        pam.passwd.askPassword(); // pam_unix asks first; an empty answer reaches Howdy.
        compare(pam.passwd.responses, [""]);
        verify(!pam.awaitingUserInput);
        verify(watchdog().running, "Howdy runs after the empty answer and stays guarded");
        wait(30);
        compare(pam.passwd.startCount, 1, "Only one automatic attempt while awake");
    }

    function test_explicit_lock_with_display_on_waits_for_wake_or_input() {
        const spy = unlockSpy();
        pam.lockSecured = true; // Manual lock: displays stay on, no inactivity flag set.
        wait(50);
        compare(pam.passwd.startCount, 0, "Locking must not start the camera by itself");
        verify(!pam.passwd.active);
        compare(spy.count, 0);
        IdleService.monitorsOff = true;
        wait(20);
        compare(pam.passwd.startCount, 0);
        IdleService.monitorsOff = false; // The wake arms one attempt.
        tryCompare(pam.passwd, "startCount", 1);
        spy.destroy();
    }

    function test_explicit_lock_starts_after_lock_screen_input() {
        pam.lockSecured = true;
        wait(50);
        compare(pam.passwd.startCount, 0);
        pam.retryFprintOnActivity();
        tryCompare(pam.passwd, "startCount", 1);
    }

    function test_input_before_lock_does_not_arm() {
        pam.retryFprintOnActivity();
        pam.lockSecured = true;
        wait(50);
        compare(pam.passwd.startCount, 0);
    }

    function test_typed_text_cancels_automatic_attempt() {
        pam.lockSecured = true;
        pam.retryFprintOnActivity(); // Key press handlers run before the text lands.
        pam.buffer = "p";
        wait(50);
        compare(pam.passwd.startCount, 0, "Typing a password must not start the camera");
    }

    function test_no_start_until_secured_and_awake() {
        IdleService.monitorsOff = true;
        pam.lockSecured = true;
        wait(20);
        compare(pam.passwd.startCount, 0);
        IdleService.monitorsOff = false;
        tryCompare(pam.passwd, "startCount", 1);
    }

    function test_policy_disables_automatic_custom_auth() {
        AdminPolicy.disableCustomLockPam = true;
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        wait(20);
        compare(pam.passwd.startCount, 0);
    }

    function test_automatic_requires_enabled_howdy_module() {
        SettingsData.pamText = "auth [success=2 default=ignore] pam_unix.so\n# auth sufficient pam_howdy.so\n";
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        wait(20);
        compare(pam.passwd.startCount, 0, "Commented Howdy must not enable camera startup");
    }

    function test_automatic_requires_password_first_stack() {
        SettingsData.pamText = "auth [success=2 default=ignore] pam_howdy.so\nauth [success=1 default=ignore] pam_unix.so\n";
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        wait(20);
        compare(pam.passwd.startCount, 0, "A Howdy-first stack would make passwords wait for the camera");
    }

    function test_missing_custom_file_uses_password_without_autostart() {
        SettingsData.pamFilePresent = false;
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        wait(20);
        compare(pam.passwd.startCount, 0);
        compare(pam.passwd.config, "login");
        pam.buffer = "test-only-password";
        pam.submitPassword();
        compare(pam.passwd.startCount, 1);
        pam.passwd.askPassword();
        compare(pam.passwd.responses[0], "test-only-password");
    }

    function test_failed_face_is_quiet_and_password_uses_new_attempt() {
        startAutomatic();
        pam.passwd.askPassword();
        compare(pam.passwd.responses, [""]);
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Failed); // No face match.
        compare(pam.state, "", "No password was entered, so nothing failed");
        verify(!pam.responseSubmitted);
        wait(20);
        compare(pam.passwd.startCount, 1, "A rejection must not trigger a camera retry loop");
        pam.buffer = "typed-test-password";
        pam.submitPassword();
        compare(pam.passwd.startCount, 2);
        pam.passwd.askPassword();
        compare(pam.passwd.responses[1], "typed-test-password");
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Failed);
        compare(pam.state, "fail", "A wrong password is still reported");
    }

    function test_manual_attempt_counts_as_this_wakes_face_attempt() {
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        pam.buffer = "wrong-test-password";
        wait(20);
        pam.submitPassword(); // The stack's Howdy fallback runs after the wrong password.
        compare(pam.passwd.startCount, 1);
        pam.passwd.askPassword();
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Failed);
        pam.buffer = "";
        wait(50);
        compare(pam.passwd.startCount, 1, "No second camera attempt in the same wake");
    }

    function test_screen_off_aborts_automatic_flow_then_retries_on_wake() {
        startAutomatic();
        pam.passwd.askPassword();
        IdleService.monitorsOff = true;
        verify(!pam.passwd.active);
        compare(pam.passwd.abortCount, 1);
        IdleService.monitorsOff = false;
        tryCompare(pam.passwd, "startCount", 2);
        wait(20);
        compare(pam.passwd.startCount, 2);
    }

    function test_sleep_aborts_automatic_flow_then_retries_on_resume() {
        startAutomatic();
        SessionService.preparingForSleep = true;
        verify(!pam.passwd.active);
        SessionService.preparingForSleep = false;
        tryCompare(pam.passwd, "startCount", 2);
    }

    function test_typed_input_survives_screen_off() {
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        pam.buffer = "partially-typed-test-secret";
        IdleService.monitorsOff = true;
        IdleService.monitorsOff = false;
        wait(20);
        compare(pam.passwd.startCount, 0);
        compare(pam.buffer, "partially-typed-test-secret");
    }

    function test_submitted_input_survives_sleep() {
        pam.lockSecured = true;
        pam.retryFprintOnActivity();
        pam.buffer = "submitted-test-secret";
        wait(20);
        pam.submitPassword();
        compare(pam.passwd.startCount, 1);
        verify(pam.responseSubmitted);
        pam.buffer = ""; // Also protect a submitted response before its prompt arrives.
        SessionService.sleepRequested = true;
        verify(pam.passwd.active);
        compare(pam.passwd.abortCount, 0);
        SessionService.sleepRequested = false;
        wait(20);
        compare(pam.passwd.startCount, 1);
        verify(pam.responseSubmitted);
    }

    function test_pending_second_factor_survives_screen_off() {
        startAutomatic();
        pam.u2fPending = true;
        IdleService.monitorsOff = true;
        verify(pam.passwd.active);
        compare(pam.passwd.abortCount, 0);
        IdleService.monitorsOff = false;
        wait(20);
        compare(pam.passwd.startCount, 1);
    }

    function test_unlock_success_reaches_existing_unlock_signal() {
        startAutomatic();
        pam.passwd.askPassword(); // Empty answer sent; Howdy matches.
        const spy = unlockSpy();
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Success);
        compare(spy.count, 1);
        verify(pam.unlockInProgress);
        spy.destroy();
    }

    function test_stalled_face_recovers_and_password_still_reaches_pam() {
        startAutomatic();
        pam.passwd.askPassword(); // Empty answer sent; Howdy then never returns.
        compare(watchdog().interval, 15000);
        tryCompare(pam, "state", "error", 17000);
        verify(!pam.passwd.active);
        verify(!pam.authBusy);
        compare(pam.passwd.startCount, 1);
        // The next attempt is manual; with pam_unix first it never reaches Howdy.
        pam.buffer = "after-stall-test-password";
        pam.submitPassword();
        compare(pam.passwd.startCount, 2);
        pam.passwd.askPassword();
        compare(pam.passwd.responses, ["", "after-stall-test-password"]);
        const spy = unlockSpy();
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Success);
        compare(spy.count, 1);
        spy.destroy();
    }

    // Review r2: password keys during the in-flight face attempt.
    function test_key_during_automatic_attempt_reaches_password() {
        startAutomatic();
        pam.passwd.askPassword(); // Empty answer sent; Howdy is still running.
        verify(watchdog().running);
        type("t");
        compare(pam.buffer, "t", "The first key must not be dropped");
        verify(!pam.passwd.active, "Typing abandons the face attempt at once");
        compare(pam.passwd.abortCount, 1);
        verify(!watchdog().running);
        type("est-only-password");
        verify(press(Qt.Key_Return));
        compare(pam.passwd.startCount, 2, "Enter starts a fresh password attempt");
        pam.passwd.askPassword();
        compare(pam.passwd.responses, ["", "test-only-password"]);
        const spy = unlockSpy();
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Success);
        compare(spy.count, 1);
        spy.destroy();
    }

    function test_key_before_empty_answer_is_kept_for_password() {
        startAutomatic(); // pam_unix has not prompted yet.
        type("k");
        verify(!pam.passwd.active);
        verify(press(Qt.Key_Return));
        compare(pam.passwd.startCount, 2);
        pam.passwd.askPassword();
        compare(pam.passwd.responses, ["k"], "The typed key, not the automatic empty answer");
    }

    function test_enter_on_empty_field_replaces_automatic_attempt() {
        startAutomatic();
        pam.passwd.askPassword();
        verify(press(Qt.Key_Return));
        compare(pam.passwd.abortCount, 1);
        compare(pam.passwd.startCount, 2);
        verify(pam.authBusy, "A submitted attempt is busy as before");
        pam.passwd.askPassword();
        compare(pam.passwd.responses, ["", ""]);
    }

    // Review r2: pam_unix nullok can succeed for a blank password before any
    // prompt, without Howdy. An automatic attempt must not unlock from that.
    function test_automatic_success_without_empty_answer_stays_locked() {
        const spy = unlockSpy();
        startAutomatic();
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Success); // No prompt was answered.
        compare(spy.count, 0);
        verify(!pam.unlockInProgress);
        compare(pam.state, "");
        verify(!pam.responseSubmitted);
        wait(20);
        compare(pam.passwd.startCount, 1, "No retry loop");
        spy.destroy();
    }
}
