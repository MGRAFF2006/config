#!/usr/bin/env python3
"""Exercise the production DMS PAM controller headlessly with inert PAM/file stubs.

No real PAM conversations, camera, desktop session or account files are opened.
The 15-second stalled-authentication check intentionally uses the real timer.
Key presses go through the pinned DMS password field's own handler.
"""

import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def write_module(root, name, files, singletons=()):
    directory = root.joinpath(*name.split('.'))
    directory.mkdir(parents=True, exist_ok=True)
    entries = [f"module {name}"]
    for component, body in files.items():
        (directory / f"{component}.qml").write_text(body)
        prefix = "singleton " if component in singletons else ""
        entries.append(f"{prefix}{component} 1.0 {component}.qml")
    (directory / "qmldir").write_text("\n".join(entries) + "\n")


def pinned_password_field(source):
    """The DMS password field's state and key handling, verbatim, up to handleKey's end."""
    widget = (source / 'Modules/Lock/Widgets/LockAuthWidget.qml').read_text()
    start = widget.index('readonly property string text: root.passwordBuffer')
    handler = widget.index('function handleKey(event) {', start)
    depth, end = 0, None
    for position in range(widget.index('{', handler), len(widget)):
        depth += {'{': 1, '}': -1}.get(widget[position], 0)
        if depth == 0:
            end = position + 1
            break
    block = widget[start:end]
    # The guard under test; fail closed if the pinned handler changed shape.
    assert end and 'root.pam.retryFprintOnActivity();' in block and 'if (root.pam.authBusy) {' in block \
        and 'insertText(event.text);' in block and 'root.pam.submitPassword();' in block, 'pinned key handler not found'
    return block


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True, help='Pristine DMS v2.1.2 UI')
    parser.add_argument('--unpatched', action='store_true', help='Demonstrate the automatic-start regression against pristine UI')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('dms_stage', ROOT / 'scripts/configure-dms-smooth-sliders.py')
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    with tempfile.TemporaryDirectory(prefix='howdy-lock-check-') as temp:
        directory = Path(temp)
        source = args.source_dir if args.unpatched else stage.stage(args.source_dir, directory / 'staged')
        production = directory / 'production'
        production.mkdir()
        shutil.copy2(source / 'Modules/Lock/Pam.qml', production / 'Pam.qml')
        imports = directory / 'imports'
        write_module(imports, 'Quickshell', {
            'Scope': 'import QtQml\nQtObject { default property list<QtObject> data }\n',
            'Quickshell': 'pragma Singleton\nimport QtQml\nQtObject { property string shellDir: "/inert-shell" }\n',
        }, ('Quickshell',))
        write_module(imports, 'Quickshell.Io', {
            'FileView': '''import QtQml
import qs.Common
QtObject {
    property string path: ""
    property bool printErrors: false
    property bool watchChanges: false
    readonly property bool loaded: path === "/etc/pam.d/dankshell" && SettingsData.pamFilePresent
    function text() { return loaded ? SettingsData.pamText : ""; }
    function reload() {}
}
''',
            'Process': 'import QtQml\nQtObject { property var command: []; property bool running: false; signal exited(int exitCode) }\n',
        })
        write_module(imports, 'Quickshell.Services.Pam', {
            'PamContext': '''import QtQml
QtObject {
    property string config: ""
    property string configDirectory: ""
    property bool active: false
    property bool responseRequired: false
    property string message: ""
    property int startCount: 0
    property int abortCount: 0
    property var responses: []
    signal pamMessage()
    signal completed(int res)
    function start() { startCount++; active = true; return true; }
    function abort() { if (active) abortCount++; active = false; responseRequired = false; }
    function respond(value) { responses = responses.concat([value]); responseRequired = false; }
    function askPassword() { responseRequired = true; message = "Password: "; pamMessage(); }
    // A PAM_TEXT_INFO/PAM_ERROR_MSG notice, e.g. Howdy's "Failure, timeout reached".
    function notice(text) { responseRequired = false; message = text; pamMessage(); }
}
''',
            'PamResult': 'pragma Singleton\nimport QtQml\nQtObject { enum Results { Success, Error, MaxTries, Failed } }\n',
        }, ('PamResult',))
        write_module(imports, 'qs.Common', {
            'SettingsData': '''pragma Singleton
import QtQml
QtObject {
    property bool lockPamExternallyManaged: true
    property string lockPamPath: "/etc/pam.d/dankshell"
    property string lockU2fPamPath: ""
    property bool lockPamInlineFprint: false
    property bool lockPamInlineU2f: false
    property bool lockFingerprintReady: false
    property bool lockU2fReady: false
    property bool enableFprint: false
    property bool enableU2f: false
    property string u2fMode: "or"
    property int maxFprintTries: 3
    property bool pamFilePresent: true
    property string pamText: ""
}
''',
            'AdminPolicy': 'pragma Singleton\nimport QtQml\nQtObject { property bool disableCustomLockPam: false }\n',
            'Paths': 'pragma Singleton\nimport QtQml\nQtObject { property string state: "/inert-state"; function strip(path) { return path; } }\n',
            'Log': 'pragma Singleton\nimport QtQml\nQtObject { function scoped(name) { return { warn: function(message) {} }; } }\n',
            'Theme': 'pragma Singleton\nimport QtQml\nQtObject { property real spacingM: 12; property real spacingXXS: 2 }\n',
        }, ('SettingsData', 'AdminPolicy', 'Paths', 'Log', 'Theme'))
        write_module(imports, 'qs.Services', {
            'SessionService': '''pragma Singleton
import QtQml
QtObject {
    property bool preparingForSleep: false
    property bool sleepRequested: false
    signal sessionResumed()
    signal lidOpened()
}
''',
            'IdleService': 'pragma Singleton\nimport QtQml\nQtObject { property bool monitorsOff: false }\n',
        }, ('SessionService', 'IdleService'))
        fixture = ROOT / 'scripts/fixtures/howdy-lock.qml'
        test = directory / 'tst_howdy_lock.qml'
        test.write_text(fixture.read_text().replace('"PRODUCTION"', '"production"')
                        .replace('// PINNED_PASSWORD_FIELD', pinned_password_field(source)))
        for name in ('runtime', 'config', 'cache', 'state', 'data'):
            (directory / name).mkdir(mode=0o700)
        env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                   QML_DISABLE_DISK_CACHE='1', QT_FORCE_STDERR_LOGGING='1', QT_LOGGING_TO_CONSOLE='1',
                   QT_LOGGING_RULES='*.debug=false', XDG_RUNTIME_DIR=str(directory / 'runtime'),
                   XDG_CONFIG_HOME=str(directory / 'config'), XDG_CACHE_HOME=str(directory / 'cache'),
                   XDG_STATE_HOME=str(directory / 'state'), XDG_DATA_HOME=str(directory / 'data'))
        command = ['/usr/lib/qt6/bin/qmltestrunner', '-input', str(test), '-import', str(imports), '-o', '-,txt']
        if args.unpatched:
            command.append('HowdyLock::test_auto_start_uses_managed_stack')
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=45)
        print(result.stdout, end='')
        if result.returncode:
            print(f'QML runner exited {result.returncode}')
            print(result.stderr, end='')
            raise SystemExit(result.returncode)
        if 'FAIL!' in result.stdout or 'QWARN' in result.stdout:
            raise SystemExit('Unexpected QML failure or warning')
        # Unresolved bindings in the fixture or production code print here.
        if '.qml:' in result.stderr:
            print(result.stderr, end='')
            raise SystemExit('Unexpected QML runtime warning')


if __name__ == '__main__':
    main()
