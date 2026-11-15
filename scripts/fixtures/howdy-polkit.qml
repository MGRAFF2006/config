import QtQuick
import QtTest
import "PRODUCTION" as Production

Item {
    QtObject {
        id: flow
        property bool isResponseRequired: false
        property string inputPrompt: ""
        property string message: "Test system action"
        property string supplementaryMessage: ""
        property bool supplementaryIsError: false
        property bool responseVisible: false
        property var submissions: []
        signal authenticationSucceeded()
        signal authenticationFailed()
        signal authenticationRequestCancelled()
        function submit(value) {
            submissions = submissions.concat([value]);
            isResponseRequired = false;
        }
    }

    Production.PolkitAuthContent { id: ui; currentFlow: flow }
    SignalSpy { id: success; target: ui; signalName: "authenticationSucceeded" }
    SignalSpy { id: closed; target: ui; signalName: "closeRequested" }

    TestCase {
        name: "HowdyPolkit"
        when: true

        function init() {
            ui.reset();
            flow.isResponseRequired = false;
            flow.submissions = [];
            flow.supplementaryMessage = "";
            flow.supplementaryIsError = false;
            success.clear();
            closed.clear();
        }

        function test_face_success_needs_no_password() {
            flow.supplementaryMessage = "Attempting facial authentication";
            compare(flow.submissions.length, 0);
            flow.authenticationSucceeded();
            compare(success.count, 1);
            compare(closed.count, 1);
            compare(flow.submissions.length, 0);
        }

        function test_timeout_leaves_password_available() {
            flow.supplementaryMessage = "Failure, timeout reached";
            flow.supplementaryIsError = true;
            flow.inputPrompt = "Password:";
            flow.isResponseRequired = true;
            compare(ui.isLoading, false);
            ui.passwordInput = "dummy-password";
            ui.submitAuth();
            compare(flow.submissions.length, 1);
            compare(flow.submissions[0], "dummy-password");
            compare(ui.passwordInput, "");
        }

        function test_typed_before_prompt_is_queued() {
            ui.passwordInput = "dummy-queued";
            ui.submitAuth();
            compare(flow.submissions.length, 0);
            flow.inputPrompt = "Password:";
            flow.isResponseRequired = true;
            compare(flow.submissions.length, 1);
            compare(flow.submissions[0], "dummy-queued");
        }

        function test_empty_submit_does_not_answer_info_notice() {
            flow.supplementaryMessage = "Attempting facial authentication";
            ui.submitAuth();
            compare(flow.submissions.length, 0);
            flow.isResponseRequired = true;
            compare(flow.submissions.length, 0);
            compare(ui.isLoading, false);
        }

        function test_failed_password_reopens_input() {
            flow.isResponseRequired = true;
            ui.passwordInput = "dummy-wrong";
            ui.submitAuth();
            compare(ui.isLoading, true);
            flow.authenticationFailed();
            compare(ui.isLoading, false);
            flow.isResponseRequired = true;
            ui.passwordInput = "dummy-next";
            ui.submitAuth();
            compare(flow.submissions.length, 2);
        }
    }
}
