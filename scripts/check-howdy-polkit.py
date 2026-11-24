#!/usr/bin/env python3
"""Check polkit installation and actual DMS dialog flow without authentication.

Default checks use temporary installer targets, real libpam with stubbed
Howdy/password/account steps and a temporary faillock tally, and the DMS
dialog against a stubbed polkit flow.
Explicit root-only --sandbox copies the vendor helper's restrictions into a
bounded private service, imports recognition libraries, opens/closes the
configured camera and checks that the faillock tally directory is mounted
writable. It reads no camera frames, writes no tally and performs no
authentication.
"""

import argparse
import configparser
import ctypes
import importlib.util
import itertools
import os
from pathlib import Path
import pwd
import re
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
    assert ("ReadWritePaths=-" + module.tally_dir()).encode() in dropin, "faillock tally must stay writable"
    assert dropin.count(b"ReadWritePaths=") == 1 and b"@" not in dropin.replace(b"#", b"")
    # The face path's pin covers exactly the system-auth that passed validation.
    assert files[module.PIN_TARGET] == module.render_pin(module.SYSTEM_AUTH.read_bytes())
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
        for workaround, accepted in (("off", True), ("input", False), ("native", False), (None, False)):
            config.write_text("[core]\n" + (f"workaround = {workaround}\n" if workaround else ""))
            try:
                module.check_workaround(config)
            except ValueError:
                assert not accepted, workaround
            else:
                assert accepted, "Howdy workaround would skip the face after the password gate: " + str(workaround)
        system_auth = root / "system-auth"
        arch = ("auth required pam_faillock.so preauth\n-auth [success=2 default=ignore] pam_systemd_home.so\n"
                "auth [success=1 default=bad] pam_unix.so try_first_pass nullok\nauth [default=die] pam_faillock.so authfail\n"
                "auth optional pam_permit.so\nauth required pam_env.so\nauth required pam_faillock.so authsucc\n"
                "account required pam_unix.so\naccount required pam_time.so\n#auth required pam_unknown.so\n")
        for accepted in (arch, "auth sufficient pam_unix.so try_first_pass likeauth nullok\n" + arch,
                         arch + "auth required /usr/lib/security/pam_env.so\n",
                         # A comment ends a line, so its backslash continues nothing.
                         arch + "# auth required pam_u2f.so \\\nauth required pam_env.so\n"):
            module.check_system_auth(accepted)
        # Every spelling Linux-PAM reads as a mandatory auth step must be refused:
        # type and control keywords are case-insensitive, and a trailing backslash
        # continues a line, also across blank and comment-only lines.
        for skipped in ("auth required pam_google_authenticator.so", "auth requisite /usr/lib/security/pam_u2f.so",
                        "auth include other-auth", "auth substack other-auth", "@include common-auth",
                        "-auth [success=ok default=die] pam_oath.so", "auth",
                        "AUTH required pam_u2f.so", "Auth Required pam_u2f.so", "-AUTH requisite pam_u2f.so",
                        "auth INCLUDE other-auth", "auth Substack other-auth",
                        "auth required \\\n    pam_u2f.so", "auth \\\n\n# key\n  required pam_u2f.so",
                        "auth\trequired\tpam_u2f.so", "auth required /opt/custom/pam_unix.so"):
            try:
                module.check_system_auth(arch + skipped + "\n")
            except ValueError:
                pass
            else:
                raise AssertionError("system-auth guard skipped by face success was accepted: " + skipped)
        # Any faillock option beyond the action and logging words could select
        # a policy the face path's plain preauth does not use.
        for custom in ("conf=/etc/security/other.conf", "dir=/var/lib/faillock", "deny=10", "unlock_time=0",
                       "even_deny_root", "local_users_only", "[dir=/run/x]"):
            try:
                module.check_system_auth(arch.replace("pam_faillock.so preauth", "pam_faillock.so preauth " + custom))
            except ValueError:
                pass
            else:
                raise AssertionError("custom pam_faillock option accepted: " + custom)
        module.check_system_auth(arch.replace("pam_faillock.so authfail", "pam_faillock.so authfail audit silent"))
        faillock_conf = root / "faillock.conf"
        for text, expected in (("# dir = /etc\n", "/run/faillock"), ("deny = 5\nsilent\n", "/run/faillock"),
                               ("dir = /var/lib/faillock/\n", "/var/lib/faillock"),
                               # Linux-PAM also accepts a whitespace-separated value.
                               ("dir /var/lib/faillock\n", "/var/lib/faillock"), ("  dir\t/run/x/y\n", "/run/x/y"),
                               ("dir=/run/x/y\n", "/run/x/y")):
            faillock_conf.write_text(text)
            assert module.tally_dir(faillock_conf) == expected, text
        for unsafe in ("= /", "= /etc", "= /run/faillock x", "= /run/../etc", "= /run/fail:lock", "= /run/faillock # tally",
                       "= run/faillock", " /etc", "\t/"):
            faillock_conf.write_text("dir" + unsafe + "\n")
            try:
                module.tally_dir(faillock_conf)
            except ValueError:
                pass
            else:
                raise AssertionError("unsafe faillock dir accepted: " + unsafe)
        faillock_conf.write_text("dir = /var/lib/faillock\n")
        system_auth.write_text(arch)
        _, planned = module.plan(faillock_conf=faillock_conf, system_auth=system_auth)
        assert b"ReadWritePaths=-/var/lib/faillock\n" in planned[module.DROPIN_TARGET]
        assert planned[module.PIN_TARGET] == module.render_pin(arch.encode())
        system_auth.write_text(arch.replace("preauth", "preauth deny=9"))
        try:
            module.plan(faillock_conf=faillock_conf, system_auth=system_auth)
        except ValueError:
            pass
        else:
            raise AssertionError("plan accepted a custom faillock policy")
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
    print("PASS: generated unit, camera/tally paths, system-auth and faillock policy validation, backups, idempotence and rollback")


PAM_PROMPT_ECHO_OFF, PAM_PROMPT_ECHO_ON, PAM_CONV_ERR, PAM_FAIL_DELAY = 1, 2, 19, 10


def check_pam():
    """Run the managed stack through real libpam, pam_exec, cmp, sha256sum and pam_faillock.

    Only Howdy, the password check and the account step are stubs. Lockout
    state lives in a temporary tally directory seeded by real pam_faillock.
    """
    pam = ctypes.CDLL("libpam.so.0")
    libc = ctypes.CDLL(None)
    libc.calloc.restype, libc.calloc.argtypes = ctypes.c_void_p, [ctypes.c_size_t, ctypes.c_size_t]
    libc.strdup.restype, libc.strdup.argtypes = ctypes.c_void_p, [ctypes.c_char_p]
    libc.free.argtypes = [ctypes.c_void_p]

    class Message(ctypes.Structure):
        _fields_ = [("style", ctypes.c_int), ("text", ctypes.c_char_p)]

    class Response(ctypes.Structure):
        _fields_ = [("resp", ctypes.c_void_p), ("retcode", ctypes.c_int)]

    callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(Message)),
                                ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p)

    class Conversation(ctypes.Structure):
        _fields_ = [("callback", callback), ("data", ctypes.c_void_p)]

    state = {}

    @callback
    def converse(count, messages, responses, data):
        replies = libc.calloc(count, ctypes.sizeof(Response))
        array = ctypes.cast(replies, ctypes.POINTER(Response))
        for index in range(count):
            message = messages[index].contents
            if message.style in (PAM_PROMPT_ECHO_OFF, PAM_PROMPT_ECHO_ON):
                state["prompts"] += 1
                if state["answer"] is None:  # the user cancels the dialog
                    libc.free(replies)
                    return PAM_CONV_ERR
                with state["trace"].open("a") as stream:
                    stream.write("answer\n")
                array[index].resp = libc.strdup(state["answer"].encode())
        responses[0] = replies
        return 0

    conversation = Conversation(converse, None)
    pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    for name in ("pam_authenticate", "pam_acct_mgmt", "pam_end"):
        getattr(pam, name).argtypes = [ctypes.c_void_p, ctypes.c_int]
    user = pwd.getpwuid(os.getuid()).pw_name.encode()
    # Skip libpam's failure delay (seconds per failed case); results are unchanged.
    no_delay = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_uint, ctypes.c_void_p)(lambda *args: None)
    pam.pam_set_item.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

    def run(root, service, authenticate=True):
        handle = ctypes.c_void_p()
        result = pam.pam_start_confdir(service, user, ctypes.byref(conversation), str(root).encode(), ctypes.byref(handle))
        assert result == 0, result
        assert pam.pam_set_item(handle, PAM_FAIL_DELAY, ctypes.cast(no_delay, ctypes.c_void_p)) == 0
        try:
            result = pam.pam_authenticate(handle, 0)
            if result == 0 and authenticate:
                assert pam.pam_acct_mgmt(handle, 0) == 0, "account step failed"
            return result
        finally:
            pam.pam_end(handle, result)

    module = load_installer()
    source = (ROOT / "system/pam.d/polkit-1").read_text()
    auth = [line for line in source.splitlines() if line.startswith("auth")]
    gate = re.fullmatch(r"auth\s+\[[^]]*\]\s+pam_exec\.so quiet quiet_log expose_authtok (.+)", auth[0])
    assert gate, "polkit-1 must ask for the password before anything else"
    assert re.fullmatch(r"auth\s+include\s+system-auth", auth[-1]), "typed passwords jump to system-auth"
    # The face guard must use faillock.conf exactly like system-auth (no options).
    assert re.findall(r"pam_faillock\.so.*", source) == ["pam_faillock.so      preauth"], "face guard must be plain preauth"

    with tempfile.TemporaryDirectory(prefix="howdy-polkit-pam-check-") as directory:
        root = Path(directory)
        trace = root / "trace"
        stub = root / "module.sh"
        stub.write_text('printf "%s\\n" "$2" >> "$1"\nexit "$3"\n')
        password = root / "password.sh"
        password.write_text('read -r typed || true\nprintf "password\\n" >> "$1"\n[ "$typed" = dummy-correct ]\n')
        killed = root / "killed.sh"
        killed.write_text("kill -KILL $$\n")
        tally = root / "tally"
        conf = root / "faillock.conf"
        conf.write_text(f"dir = {tally}\ndeny = 3\nunlock_time = 600\n")
        faillock = f"pam_faillock.so conf={conf}"
        system_auth = (
            # Arch's system-auth shape, with real faillock and a stubbed pam_unix.
            f"auth required {faillock} preauth\n"
            f"auth [success=1 default=bad] pam_exec.so quiet expose_authtok /bin/sh {password} {trace}\n"
            f"auth [default=die] {faillock} authfail\n"
            f"auth required {faillock} authsucc\n"
            f"account required pam_exec.so quiet /bin/sh {stub} {trace} account 0\n")
        # A mandatory factor added to system-auth after the face option was installed.
        added_factor = f"auth required pam_exec.so quiet /bin/sh {stub} {trace} key 1\n"
        pin = root / "polkit-system-auth.sha256"
        pin.write_bytes(module.render_pin(system_auth.encode()).replace(str(module.SYSTEM_AUTH).encode(), str(root / "system-auth").encode()))
        (root / "seed").write_text(f"auth required {faillock} authfail\n")
        # Gate failures, all reported as PAM_SYSTEM_ERR like a typed password:
        # the program cannot run, is killed, or exits non-zero without reading.
        broken_gates = {"missing": "/nonexistent/gate", "killed": f"/bin/sh {killed}", "fails": "/bin/false"}
        results = []
        variants = [("installed", tallies) for tallies in (0, 1, 3)]
        variants += [(name, 0) for name in (*broken_gates, "system-auth-changed")]
        for (variant, tallies), answer, face in itertools.product(variants, (None, "", "dummy-correct", "dummy-wrong"), (True, False)):
            shutil.rmtree(tally, ignore_errors=True)
            tally.mkdir()
            (root / "system-auth").write_text(system_auth)
            state.update(prompts=0, answer="", trace=trace)
            for _ in range(tallies):  # real failures; 3 reaches deny=3
                run(root, b"seed", authenticate=False)
            assert len(list(tally.iterdir())) == (1 if tallies else 0)
            if variant == "system-auth-changed":
                (root / "system-auth").write_text(system_auth + added_factor)
            trace.write_text("")
            stack = (source.replace("pam_faillock.so", faillock)
                     .replace("pam_howdy.so", f"pam_exec.so quiet /bin/sh {stub} {trace} face {0 if face else 1}")
                     .replace(str(module.PIN_TARGET), str(pin)))
            if variant in broken_gates:
                stack = stack.replace(auth[0], auth[0].replace(gate.group(1), broken_gates[variant]))
            (root / "polkit-1").write_text(stack)
            state.update(prompts=0, answer=answer)
            result = run(root, b"polkit-1")
            reached = [step for step in trace.read_text().splitlines() if step != "account"]
            locked = tallies >= 3
            case = dict(variant=variant, tallies=tallies, answer=answer, face=face, result=result, reached=reached)
            assert state["prompts"] == 1, ("exactly one prompt, before any method", case)
            if answer is None:
                expected, success = [], False
            elif variant in broken_gates:
                # Never the face: the answer, even an empty one, is only a password.
                expected, success = ["answer", "password"], answer == "dummy-correct"
            elif variant == "system-auth-changed":
                # Face fails closed; system-auth (with its new factor) decides passwords.
                expected = {"": ["answer"], "dummy-correct": ["answer", "password", "key"]}.get(answer, ["answer", "password"])
                success = False
            elif answer == "":
                expected, success = (["answer"] if locked else ["answer", "face"]), face and not locked
            else:
                expected, success = ["answer", "password"], answer == "dummy-correct" and not locked
            assert reached == expected, ("wrong method order or a method ran unasked", case)
            assert (result == 0) == success, ("lockout bypassed or a method lost", case)
            results.append(case)
        assert any(case["result"] == 0 and case["tallies"] == 1 and case["answer"] == "" for case in results)
    print("PASS: real libpam/pam_exec/cmp/sha256sum/pam_faillock: nothing runs before the answer, only an empty answer"
          " asks for the face, typed password goes to system-auth only, a failing gate never reaches the face,"
          " a changed system-auth turns the face off, existing and locked tallies honoured by both, cancel denies")


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
camera, user, tally = sys.argv[1:]
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
assert os.access("/usr/bin/cmp", os.X_OK), "password gate needs cmp"
assert os.access("/usr/bin/sha256sum", os.X_OK), "face path needs sha256sum for its system-auth pin"
pin = Path("/etc/howdy/polkit-system-auth.sha256")
if pin.exists():  # written by install-howdy-polkit.py --apply
    pin.read_bytes()
if Path(tally).is_dir():  # tmpfiles creates it at boot; faillock opens tallies read-write
    assert not os.statvfs(tally).f_flag & os.ST_RDONLY, "faillock tally directory is read-only"
print("HOWDY_POLKIT_SANDBOX_PASS: libraries, models, lid, noncapturing camera open, writable tally", flush=True)
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
        content += ("\n[Service]\nExecStart=\nExecStart=/usr/bin/python3 " + str(probe) + " " + camera + " " + user + " " + module.tally_dir()
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
