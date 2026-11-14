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
        SettingsData.pamText = "auth [success=2 default=ignore] pam_howdy.so\nauth required pam_unix.so\n";
        AdminPolicy.disableCustomLockPam = false;
        SessionService.preparingForSleep = false;
        SessionService.sleepRequested = false;
        IdleService.monitorsOff = false;
        wait(1);
    }

    function cleanup() {
        pam.lockSecured = false;
        pam.resetAuthFlows();
        wait(1);
    }

    function startAutomatic() {
        pam.lockSecured = true;
        tryCompare(pam.passwd, "startCount", 1);
        verify(pam.passwd.active);
    }

    function test_auto_start_uses_managed_stack() {
        startAutomatic();
        compare(pam.passwd.config, "dankshell");
        compare(pam.passwd.configDirectory, "/etc/pam.d");
        verify(pam.authBusy);
        verify(watchdog().running, "Automatic authentication needs stall recovery");
        wait(30);
        compare(pam.passwd.startCount, 1, "Only one automatic attempt while awake");
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
        wait(20);
        compare(pam.passwd.startCount, 0);
    }

    function test_automatic_requires_enabled_howdy_module() {
        SettingsData.pamText = "# auth sufficient pam_howdy.so\nauth required pam_unix.so\n";
        pam.lockSecured = true;
        wait(20);
        compare(pam.passwd.startCount, 0, "Commented Howdy must not enable camera startup");
    }

    function test_missing_custom_file_uses_password_without_autostart() {
        SettingsData.pamFilePresent = false;
        pam.lockSecured = true;
        wait(20);
        compare(pam.passwd.startCount, 0);
        compare(pam.passwd.config, "login");
        pam.buffer = "test-only-password";
        pam.submitPassword();
        compare(pam.passwd.startCount, 1);
        pam.passwd.askPassword();
        compare(pam.passwd.responses[0], "test-only-password");
    }

    function test_timeout_prompt_waits_for_typed_submission() {
        startAutomatic();
        pam.passwd.askPassword(); // A Howdy timeout advances the same PAM conversation.
        verify(pam.awaitingUserInput);
        verify(!pam.authBusy);
        verify(!watchdog().running, "The watchdog must not interrupt a password prompt");
        compare(pam.passwd.responses.length, 0, "No empty password is auto-submitted");
        pam.buffer = "typed-test-password";
        pam.submitPassword();
        compare(pam.passwd.responses.length, 1);
        compare(pam.passwd.responses[0], "typed-test-password");
        compare(pam.passwd.startCount, 1);
        verify(watchdog().running);
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Failed);
        wait(20);
        compare(pam.passwd.startCount, 1, "A rejection must not trigger a camera retry loop");
    }

    function test_screen_off_aborts_empty_flow_then_retries_on_wake() {
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

    function test_sleep_aborts_empty_flow_then_retries_on_resume() {
        startAutomatic();
        SessionService.preparingForSleep = true;
        verify(!pam.passwd.active);
        SessionService.preparingForSleep = false;
        tryCompare(pam.passwd, "startCount", 2);
    }

    function test_typed_input_survives_screen_off() {
        startAutomatic();
        pam.passwd.askPassword();
        pam.buffer = "partially-typed-test-secret";
        IdleService.monitorsOff = true;
        verify(pam.passwd.active);
        compare(pam.passwd.abortCount, 0);
        IdleService.monitorsOff = false;
        wait(20);
        compare(pam.passwd.startCount, 1);
        compare(pam.buffer, "partially-typed-test-secret");
    }

    function test_submitted_input_survives_sleep() {
        startAutomatic();
        pam.buffer = "submitted-test-secret";
        pam.submitPassword();
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
        const signal = Qt.createQmlObject('import QtTest; SignalSpy {}', this);
        signal.target = pam;
        signal.signalName = "unlockRequested";
        pam.passwd.active = false;
        pam.passwd.completed(PamResult.Success);
        compare(signal.count, 1);
        verify(pam.unlockInProgress);
        signal.destroy();
    }

    function test_stalled_auto_auth_recovers_after_existing_watchdog() {
        startAutomatic();
        compare(watchdog().interval, 15000);
        tryCompare(pam, "state", "error", 17000);
        verify(!pam.passwd.active);
        verify(!pam.authBusy);
        compare(pam.passwd.startCount, 1);
    }
}
