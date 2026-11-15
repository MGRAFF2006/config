#!/usr/bin/env python3
"""Check polkit installation and actual DMS dialog flow without authentication.

Default checks use inert UI/PAM-flow stubs and temporary installer targets.
Explicit root-only --sandbox copies the vendor helper's restrictions into a
bounded private service, imports recognition libraries and opens/closes the
configured camera. It reads no camera frames and performs no authentication.
"""

import argparse
import configparser
import ctypes
import importlib.util
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def load_installer():
    spec = importlib.util.spec_from_file_location("howdy_polkit", ROOT / "scripts/install-howdy-polkit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_installer(module):
    camera, files = module.plan()
    dropin = files[module.DROPIN_TARGET]
    assert b"PrivateDevices=no" not in dropin and b"char-video4linux" not in dropin
    assert b"BindPaths=-" in dropin and b"DeviceAllow=" in dropin
    assert camera.encode() + b" rw" in dropin
    if ":" in camera:
        assert b"\\x3a" in dropin
    module.verify_unit(dropin)
    with tempfile.TemporaryDirectory(prefix="howdy-polkit-install-check-") as directory:
        root = Path(directory)
        config = root / "config.ini"
        for invalid in ("/dev/video0 %n", "/etc/shadow", "/dev/../etc/shadow", "/dev/video0\\nDeviceAllow=char-*"):
            config.write_text("[video]\ndevice_path=" + invalid + "\n")
            try:
                module.camera_path(config)
            except (ValueError, configparser.Error):
                pass
            else:
                raise AssertionError("Unsafe camera path accepted: " + repr(invalid))
        path = root / "target.conf"
        path.write_bytes(b"before")
        path.chmod(0o640)
        reloads = []
        reload = lambda: reloads.append(True)
        assert module.install_files({path: b"after"}, root / "backup", reload)
        assert path.read_bytes() == b"after" and len(reloads) == 1
        saved = root / "backup" / path.relative_to("/")
        assert saved.read_bytes() == b"before" and saved.stat().st_mode & 0o777 == 0o640
        assert not module.install_files({path: b"after"}, root / "unused", reload)
        assert not (root / "unused").exists() and len(reloads) == 1
        missing = root / "new.conf"

        def fail_reload():
            raise subprocess.CalledProcessError(1, "test reload")

        try:
            module.install_files({path: b"changed", missing: b"new"}, root / "rollback", fail_reload)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("Reload failure was hidden")
        assert path.read_bytes() == b"after" and not missing.exists()
        source = root / "shared.conf"
        source.write_bytes(b"shared")
        alias = root / "alias.conf"
        alias.symlink_to(source)
        try:
            module.install_files({alias: b"replacement"}, root / "symlink-rollback", fail_reload)
        except subprocess.CalledProcessError:
            pass
        else:
            raise AssertionError("Reload failure was hidden")
        assert alias.is_symlink() and alias.read_bytes() == source.read_bytes() == b"shared"
    print("PASS: generated unit, path validation, backups, idempotence and rollback")


def check_pam():
    # Exercise the actual control directives through libpam. Only module work
    # is substituted; no live account authentication or secrets are involved.
    pam = ctypes.CDLL("libpam.so.0")
    callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

    class Conversation(ctypes.Structure):
        _fields_ = [("callback", callback), ("data", ctypes.c_void_p)]

    @callback
    def unexpected_prompt(count, messages, responses, data):
        return 19

    conversation = Conversation(unexpected_prompt, None)
    pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    for name in ("pam_authenticate", "pam_acct_mgmt", "pam_end"):
        getattr(pam, name).argtypes = [ctypes.c_void_p, ctypes.c_int]
    with tempfile.TemporaryDirectory(prefix="howdy-polkit-pam-check-") as directory:
        root = Path(directory)
        trace = root / "trace"
        helper = root / "module.sh"
        helper.write_text('printf "%s\\n" "$2" >> "$1"\nexit "$3"\n')
        source = (ROOT / "system/pam.d/polkit-1").read_text()
        for face, password, account in ((True, False, True), (False, True, True), (False, False, True), (True, False, False)):
            trace.write_text("")
            module = f"pam_exec.so quiet /bin/sh {helper} {trace}"
            (root / "check").write_text(source.replace("pam_howdy.so", f"{module} face {0 if face else 1}"))
            (root / "system-auth").write_text(f"auth required {module} password {0 if password else 1}\naccount required {module} account {0 if account else 1}\n")
            handle = ctypes.c_void_p()
            result = pam.pam_start_confdir(b"check", b"inert-user", ctypes.byref(conversation), str(root).encode(), ctypes.byref(handle))
            assert result == 0, result
            try:
                result = pam.pam_authenticate(handle, 0)
                assert (result == 0) == (face or password), (face, password, result)
                reached = trace.read_text().splitlines()
                assert reached == (["face"] if face else ["face", "password"]), reached
                if result == 0:
                    result = pam.pam_acct_mgmt(handle, 0)
                    assert (result == 0) == account, ("account prerequisite bypassed", result)
                    assert trace.read_text().splitlines()[-1] == "account"
            finally:
                pam.pam_end(handle, result)
    print("PASS: real libpam face-first authorization, password fallback, denial and account guards")


def write_module(root, name, files, singletons=()):
    directory = root.joinpath(*name.split("."))
    directory.mkdir(parents=True, exist_ok=True)
    entries = ["module " + name]
    for component, body in files.items():
        (directory / (component + ".qml")).write_text(body)
        entries.append(("singleton " if component in singletons else "") + component + " 1.0 " + component + ".qml")
    (directory / "qmldir").write_text("\n".join(entries) + "\n")


def check_dialog(source):
    with tempfile.TemporaryDirectory(prefix="howdy-polkit-dialog-check-") as directory:
        root = Path(directory)
        (root / "Modals").mkdir()
        (root / "Common").mkdir()
        shutil.copy2(source / "Modals/PolkitAuthContent.qml", root / "Modals")
        shutil.copy2(source / "Common/PamStack.js", root / "Common")
        imports = root / "imports"
        write_module(imports, "Quickshell.Io", {
            "FileView": 'import QtQml\nQtObject { property string path; property bool printErrors; signal loaded(); signal loadFailed(); function text(){return "";} }',
        })
        write_module(imports, "qs.Common", {
            "I18n": 'pragma Singleton\nimport QtQml\nQtObject { function tr(s,c){return s;} }',
            "Theme": '''pragma Singleton
import QtQuick
QtObject { property real fontSizeSmall: 12; property real fontSizeMedium: 14; property real fieldHeightLarge: 36; property color error: "red"; property color onSurfaceVariant: "white"; property color surfaceText: "white"; }''',
        }, ("I18n", "Theme"))
        write_module(imports, "qs.Services", {
            "PolkitService": 'pragma Singleton\nimport QtQml\nQtObject { property var agent: null; property bool authFailed: false; }',
        }, ("PolkitService",))
        write_module(imports, "qs.DCommon.Widgets", {
            "DDialog": '''import QtQuick
Item { property string title; property string supportingText; property string iconName; property bool acceptEnabled; property real actionWidth: 100; property list<QtObject> actions; signal rejected(); signal accepted(); }''',
            "DButton": '''import QtQuick
Item { property real maximumWidth; property bool wrapText; property string text; property string variant; property bool busy; signal clicked(); }''',
            "StyledText": 'import QtQuick\nText {}',
            "DTextField": '''import QtQuick
TextInput { property bool outlined; property real controlHeight; property string labelText; property bool isError; property string supportingText; property string leftIconName; property color textColor; property bool showPasswordToggle; property bool passwordVisible; property string placeholderText; }''',
        })
        fixture = (ROOT / "scripts/fixtures/howdy-polkit.qml").read_text()
        test = root / "tst_howdy_polkit.qml"
        test.write_text(fixture.replace('"PRODUCTION"', '"Modals"'))
        for name in ("runtime", "config", "cache", "state", "data"):
            (root / name).mkdir(mode=0o700)
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", QML_DISABLE_DISK_CACHE="1",
                   XDG_RUNTIME_DIR=str(root / "runtime"), XDG_CONFIG_HOME=str(root / "config"), XDG_CACHE_HOME=str(root / "cache"),
                   XDG_STATE_HOME=str(root / "state"), XDG_DATA_HOME=str(root / "data"))
        result = subprocess.run(["/usr/lib/qt6/bin/qmltestrunner", "-input", str(test), "-import", str(imports), "-o", "-,txt"],
                                env=env, capture_output=True, text=True, timeout=20)
        print(result.stdout, end="")
        if result.returncode or "QWARN" in result.stdout:
            raise AssertionError(result.stderr + result.stdout)


SANDBOX_PROBE = '''import json, os, stat, sys
from pathlib import Path
import cv2, dlib, numpy
camera, user = sys.argv[1:]
s = os.stat(camera)
assert stat.S_ISCHR(s.st_mode), "camera is not a character device"
assert not os.path.islink(camera), "configured alias was not mounted into private /dev"
assert not Path("/dev/tpmrm0").exists(), "TPM must stay outside this helper"
assert not Path("/dev/dri").exists(), "GPU devices must stay outside this helper"
models = json.loads(Path("/etc/howdy/models", user + ".dat").read_text())
assert models and all(len(v) == 128 for model in models for v in model["data"])
for path in Path("/proc/acpi/button/lid").glob("*/state"):
    path.read_text()
dlib.get_frontal_face_detector()
dlib.shape_predictor("/usr/share/dlib-data/shape_predictor_5_face_landmarks.dat")
dlib.face_recognition_model_v1("/usr/share/dlib-data/dlib_face_recognition_resnet_model_v1.dat")
fd = os.open(camera, os.O_RDWR | os.O_NONBLOCK | os.O_CLOEXEC)
os.close(fd)
print("HOWDY_POLKIT_SANDBOX_PASS: libraries, models, lid and noncapturing camera open", flush=True)
'''


def check_sandbox(module, user):
    if os.geteuid() != 0:
        raise SystemExit("--sandbox requires root; it opens/closes the camera without capturing frames")
    pwd.getpwnam(user)
    camera, files = module.plan()
    name = "howdy-polkit-probe-" + uuid.uuid4().hex[:12]
    unit = Path("/run/systemd/system") / (name + ".service")
    with tempfile.TemporaryDirectory(prefix=name + "-", dir="/run") as directory:
        probe = Path(directory) / "probe.py"
        probe.write_text(SANDBOX_PROBE)
        # Keep every vendor restriction, replacing only the executable and socket
        # I/O plumbing. A separate unit never services real polkit requests.
        content = module.VENDOR_UNIT.read_bytes() + b"\n" + files[module.DROPIN_TARGET]
        content += ("\n[Service]\nExecStart=\nExecStart=/usr/bin/python3 " + str(probe) + " " + camera + " " + user
                    + "\nStandardInput=null\nStandardOutput=journal\nStandardError=journal\nSuccessExitStatus=\nTimeoutStartSec=15s\n").encode()
        unit.write_bytes(content)
        try:
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            result = subprocess.run(["systemctl", "start", unit.name], capture_output=True, text=True, timeout=20)
            logs = subprocess.check_output(["journalctl", "-b", "-u", unit.name, "--no-pager", "-o", "cat"], text=True)
            print(logs, end="")
            if result.returncode or "HOWDY_POLKIT_SANDBOX_PASS:" not in logs:
                raise AssertionError(result.stderr + "Sandbox probe failed")
        finally:
            subprocess.run(["systemctl", "stop", unit.name], check=False, capture_output=True)
            subprocess.run(["systemctl", "reset-failed", unit.name], check=False, capture_output=True)
            unit.unlink(missing_ok=True)
            subprocess.run(["systemctl", "daemon-reload"], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="DMS UI; defaults to the current dms.path")
    parser.add_argument("--sandbox", action="store_true", help="Root-only copied-vendor sandbox check, no captured frames")
    parser.add_argument("--user", default=os.environ.get("SUDO_USER") or pwd.getpwuid(os.getuid()).pw_name)
    args = parser.parse_args()
    module = load_installer()
    if args.sandbox:
        check_sandbox(module, args.user)
        return
    check_installer(module)
    check_pam()
    source = args.source_dir or Path(Path(f"/run/user/{os.getuid()}/dms.path").read_text().strip())
    check_dialog(source)


if __name__ == "__main__":
    main()
