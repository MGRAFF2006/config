import QtQuick
import QtTest
import Quickshell.Services.Pam
import qs.Common
import qs.Services
import "PRODUCTION" as Production

TestCase {
    name: "HowdyLock"
    when: true

    Production.Pam { id: pam }

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
        verify(pam.authBusy);
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
}
