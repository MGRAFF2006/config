#!/usr/bin/env python3
"""Exercise managed auth control flow with real libpam and simulated auth results.

No camera, passwords, root privileges or live PAM changes are needed. pam_exec
records which modules libpam reaches, substituting only the module operation.
The lock stack's pam_unix line also runs for real, against fake accounts in a
bubblewrap user namespace. Also runs the installer's DMS settings step against
fixture homes.
"""

import argparse
import ctypes
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MANAGED_LOCK = "/etc/pam.d/dankshell"


def check_settings_editor():
    """The installer edits the settings file DMS 2.1 reads, never replacing a custom stack."""
    installer = (ROOT / "scripts/install-pam-keyring-howdy.sh").read_text()
    assert 'scripts/configure-dms-lock-pam.py" "$dms_config_home"' in installer, "installer no longer runs the settings step"
    script = ROOT / "scripts/configure-dms-lock-pam.py"
    flags = {"greeterPamExternallyManaged": True, "lockPamExternallyManaged": True}
    legacy_text = json.dumps({"lockPamPath": "/etc/pam.d/legacy-untouched"}) + "\n"

    def run(config, before, legacy="absent"):
        """legacy: "absent", "separate" (its own file) or "symlink" (laptop layout)."""
        shutil.rmtree(config, ignore_errors=True)
        canonical = config / "dms/settings.json"
        if before is not None:
            canonical.parent.mkdir(parents=True)
            canonical.write_text(json.dumps({"other": 1, **before}, indent=2) + "\n")
        if legacy == "separate":
            (config / "DankMaterialShell").mkdir(parents=True)
            (config / "DankMaterialShell/settings.json").write_text(legacy_text)
        elif legacy == "symlink":
            (config / "DankMaterialShell").symlink_to("dms")
        original = canonical.read_text() if before is not None else None
        result = subprocess.run(["python3", "-I", str(script), str(config)], capture_output=True, text=True)
        if legacy == "separate":
            assert (config / "DankMaterialShell/settings.json").read_text() == legacy_text, "edited the legacy file"
        return result, canonical, original

    cases = (
        ({}, MANAGED_LOCK),
        ({"lockPamPath": ""}, MANAGED_LOCK),
        ({**flags, "lockPamPath": MANAGED_LOCK}, MANAGED_LOCK),
        ({"lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
        ({**flags, "lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
    )
    with tempfile.TemporaryDirectory(prefix="howdy-settings-check-") as directory:
        config = Path(directory) / "config"
        for legacy in ("absent", "separate", "symlink"):
            for before, expected in cases:
                result, canonical, original = run(config, before, legacy)
                assert result.returncode == 0, (before, legacy, result.stderr)
                after = json.loads(canonical.read_text())
                assert after["lockPamPath"] == expected, (before, legacy, after)
                assert all(after[key] is True for key in flags), (before, legacy, after)
                assert after["other"] == 1, (before, legacy, after)
                custom = expected != MANAGED_LOCK
                assert custom == ("kept custom lockPamPath" in result.stderr), (before, result.stderr)
                if before.keys() >= flags.keys() and before.get("lockPamPath"):
                    assert canonical.read_text() == original, ("rewrote unchanged settings", before, legacy)
        # DMS has not created its settings yet: warn and fail without writing anywhere.
        for legacy in ("absent", "separate"):
            result, canonical, _ = run(config, None, legacy)
            assert result.returncode == 1 and "not found" in result.stderr, (legacy, result)
            assert not canonical.exists(), legacy
    print("PASS: installer settings: DMS 2.1 settings file selected (legacy path ignored), custom lockPamPath preserved")


pam = ctypes.CDLL("libpam.so.0")
conversation = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


class Conversation(ctypes.Structure):
    _fields_ = [("callback", conversation), ("data", ctypes.c_void_p)]


pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]

BLANK_USER, SECRET_USER = "howdy-check-blank", "howdy-check-secret"
SECRET = "correct-test-password"
# openssl passwd -6 -salt howdycheck correct-test-password
SECRET_HASH = "$6$howdycheck$f00Do71TijHH6sFWun1Nc6gwmEz5vSFKxvQCZfbxNkVfUiPKRO/IBYYB6LdYDr68PM7cmYScP6ganTL8MYY3d."
STUB = '#!/bin/sh\nprintf "%s\\n" "$2" >> "$1"\n[ "$3" = stall ] && { sleep 20; exit 1; }\nexit "$3"\n'


class Message(ctypes.Structure):
    _fields_ = [("style", ctypes.c_int), ("text", ctypes.c_char_p)]


class Response(ctypes.Structure):
    _fields_ = [("resp", ctypes.c_void_p), ("retcode", ctypes.c_int)]


def real_unix_child(directory):
    """Runs inside the user namespace: real pam_unix, stubbed Howdy and guards."""
    libc = ctypes.CDLL(None)
    libc.calloc.restype = ctypes.c_void_p
    libc.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    libc.strdup.restype = ctypes.c_void_p
    libc.strdup.argtypes = [ctypes.c_char_p]
    root = Path(directory)
    trace = root / "trace"
    lines, cases = json.loads((root / "cases.json").read_text())
    results = []
    for user, answer, face, nullok in cases:
        prompts = []

        @conversation
        def reply(count, messages, responses, data):
            replies = ctypes.cast(libc.calloc(count, ctypes.sizeof(Response)), ctypes.POINTER(Response))
            for i in range(count):
                message = ctypes.cast(messages, ctypes.POINTER(ctypes.POINTER(Message)))[i].contents
                if message.style in (1, 2):  # PAM_PROMPT_ECHO_OFF / ECHO_ON
                    prompts.append(message.style)
                    replies[i].resp = libc.strdup(answer.encode())
            ctypes.cast(responses, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.cast(replies, ctypes.c_void_p)
            return 0

        stack = []
        for kind, control, name, options in lines:
            if name == "pam_unix.so":
                stack.append(f"{kind} {control} {name} {options}{' nullok' if nullok else ''}")
            elif name == "pam_deny.so":
                stack.append(f"{kind} {control} {name}")
            else:
                code = 1 if name == "pam_howdy.so" and not face else 0
                stack.append(f"{kind} {control} pam_exec.so quiet /bin/sh {root / 'module.sh'} {trace} {name} {code}")
        (root / "check").write_text("\n".join(stack) + "\n")
        trace.write_text("")
        conv = Conversation(reply, None)
        handle = ctypes.c_void_p()
        result = pam.pam_start_confdir(b"check", user.encode(), ctypes.byref(conv), str(root).encode(), ctypes.byref(handle))
        assert result == 0, ("pam_start_confdir", result)
        try:
            result = pam.pam_authenticate(handle, 0)  # Quickshell passes no flags either.
        finally:
            pam.pam_end(handle, result)
        results.append({"success": result == 0, "prompts": len(prompts), "howdy": "pam_howdy.so" in trace.read_text().split()})
    print(json.dumps(results))


def check_real_unix(pam_root):
    """The automatic lock attempt answers with an empty password; only Howdy may accept it."""
    bwrap = shutil.which("bwrap")
    assert bwrap, "bwrap is required to run real pam_unix against fake accounts"
    lines = [list(re.match(r"(-?auth)\s+(\[[^]]+\]|\S+)\s+(\S+)\s*(.*)", line).groups())
             for line in (pam_root / "dankshell").read_text().splitlines() if re.match(r"-?auth\s", line)]
    # (user, answer, face matches, add nullok as a negative control) -> (unlocks, Howdy reached)
    cases = (
        ((BLANK_USER, "", False, False), (False, True)),
        ((BLANK_USER, "", True, False), (True, True)),
        ((SECRET_USER, "", False, False), (False, True)),
        ((SECRET_USER, "", True, False), (True, True)),
        ((SECRET_USER, SECRET, False, False), (True, False)),
        # Control: proves the fake blank account is read; nullok skips Howdy.
        ((BLANK_USER, "", False, True), (True, False)),
    )
    with tempfile.TemporaryDirectory(prefix="howdy-unix-check-") as directory:
        root = Path(directory)
        (root / "module.sh").write_text(STUB)
        (root / "module.sh").chmod(0o755)
        (root / "passwd").write_text(f"root:x:0:0::/root:/bin/sh\n{BLANK_USER}:x:4242:4242::/nonexistent:/bin/sh\n{SECRET_USER}:x:4243:4243::/nonexistent:/bin/sh\n")
        (root / "shadow").write_text(f"root:!*:1::::::\n{BLANK_USER}::1::::::\n{SECRET_USER}:{SECRET_HASH}:1::::::\n")
        (root / "group").write_text("root:x:0:\nhowdy-check:x:4242:\n")
        (root / "nsswitch.conf").write_text("passwd: files\ngroup: files\nshadow: files\n")
        (root / "cases.json").write_text(json.dumps([lines, [case for case, _ in cases]]))
        command = [bwrap, "--unshare-user", "--uid", "0", "--gid", "0", "--ro-bind", "/", "/", "--dev", "/dev",
                   "--proc", "/proc", "--tmpfs", "/tmp", "--bind", str(root), str(root), "--die-with-parent"]
        for name in ("passwd", "shadow", "group", "nsswitch.conf"):
            command += ["--ro-bind", str(root / name), f"/etc/{name}"]
        command += [sys.executable, "-I", str(Path(__file__).resolve()), "--real-unix-child", str(root)]
        output = subprocess.run(command, capture_output=True, text=True, check=True, timeout=60).stdout
        for (case, (unlocks, howdy)), result in zip(cases, json.loads(output), strict=True):
            assert result["success"] == unlocks, ("dankshell real pam_unix", case, result)
            assert result["howdy"] == howdy, ("dankshell real pam_unix", case, result)
            if not case[3]:
                assert result["prompts"] == 1, ("pam_unix must ask before Howdy", case, result)
    print("PASS: dankshell: real pam_unix rejects an empty answer, even for a blank-password account; only Howdy accepts it")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pam-root", type=Path, default=Path(__file__).resolve().parents[1] / "system/pam.d")
    parser.add_argument("--real-unix-child", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.real_unix_child:
        real_unix_child(args.real_unix_child)
        return

    @conversation
    def unexpected_prompt(count, messages, responses, data):
        return 19  # PAM_CONV_ERR: simulated modules should never prompt.

    conv = Conversation(unexpected_prompt, None)
    with tempfile.TemporaryDirectory(prefix="howdy-pam-check-") as directory:
        root = Path(directory)
        trace = root / "trace"
        module = root / "module.sh"
        # "stall" stands in for a camera that never returns.
        module.write_text(STUB)
        module.chmod(0o755)
        for service in ("greetd", "dankshell"):
            lines = []
            for line in (args.pam_root / service).read_text().splitlines():
                match = re.match(r"(-?auth)\s+(\[[^]]+\]|\S+)\s+(\S+)", line)
                if match:
                    lines.append(match.groups())

            def authenticate(face, password, failed_guard=None):
                trace.write_text("")
                stack = []
                for kind, control, name in lines:
                    if name == "pam_deny.so":
                        stack.append(f"{kind} {control} {name}")
                        continue
                    result = face if name == "pam_howdy.so" else password if name == "pam_unix.so" else name != failed_guard
                    code = "stall" if result == "stall" else 0 if result else 1
                    stack.append(f"{kind} {control} pam_exec.so quiet /bin/sh {module} {trace} {name} {code}")
                (root / "check").write_text("\n".join(stack) + "\n")
                handle = ctypes.c_void_p()
                result = pam.pam_start_confdir(b"check", b"howdy-test", ctypes.byref(conv), str(root).encode(), ctypes.byref(handle))
                assert result == 0, ("pam_start_confdir", result)
                try:
                    result = pam.pam_authenticate(handle, 0)
                finally:
                    pam.pam_end(handle, result)
                return result == 0, trace.read_text().splitlines()

            # Password first: a correct password never reaches Howdy, so a stalled
            # camera cannot delay it; an empty or wrong one falls through to Howdy.
            for face, password, expected in ((True, False, True), (False, True, True), ("stall", True, True), (False, False, False)):
                started = time.monotonic()
                success, reached = authenticate(face, password)
                assert success == expected, (service, face, password, success, reached)
                methods = [name for name in reached if name in ("pam_howdy.so", "pam_unix.so")]
                assert methods == (["pam_unix.so"] if password else ["pam_unix.so", "pam_howdy.so"]), (service, "order", methods)
                assert time.monotonic() - started < 10, (service, "password waited for a stalled camera")
                if expected:
                    continuation = "pam_kwallet5.so" if service == "greetd" else "pam_env.so"
                    assert continuation in reached, (service, "skipped continuation", reached)
            # A successful face cannot bypass existing prerequisite failures.
            guards = ("pam_securetty.so", "pam_nologin.so") if service == "greetd" else ("pam_nologin.so", "pam_shells.so")
            for guard in guards:
                success, reached = authenticate(True, False, guard)
                assert not success, (service, "bypassed guard", guard, reached)
            print(f"PASS: {service}: password first (independent of a stalled camera), Howdy fallback, deny both failures, continuation and prerequisite guards")
    check_real_unix(args.pam_root)
    check_settings_editor()


if __name__ == "__main__":
    main()
