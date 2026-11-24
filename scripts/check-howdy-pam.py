#!/usr/bin/env python3
"""Exercise managed auth control flow with real libpam and simulated auth results.

No camera, passwords, root privileges or live PAM changes are needed. pam_exec
records which modules libpam reaches, substituting only the module operation.
Also runs the installer's DMS settings editor against JSON fixtures.
"""

import argparse
import ctypes
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MANAGED_LOCK = "/etc/pam.d/dankshell"


def check_settings_editor():
    """The installer selects the managed lock stack but never replaces a custom one."""
    installer = (ROOT / "scripts/install-pam-keyring-howdy.sh").read_text()
    editor = re.search(r"python3 - \"\$dms_settings\" <<'PY'\n(.*?)\nPY\n", installer, re.S)
    assert editor, "settings editor heredoc not found in install-pam-keyring-howdy.sh"
    flags = {"greeterPamExternallyManaged": True, "lockPamExternallyManaged": True}
    cases = (
        ({}, MANAGED_LOCK),
        ({"lockPamPath": ""}, MANAGED_LOCK),
        ({**flags, "lockPamPath": MANAGED_LOCK}, MANAGED_LOCK),
        ({"lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
        ({**flags, "lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
    )
    with tempfile.TemporaryDirectory(prefix="howdy-settings-check-") as directory:
        settings = Path(directory) / "settings.json"
        for before, expected in cases:
            settings.write_text(json.dumps({"other": 1, **before}, indent=2) + "\n")
            original = settings.read_text()
            result = subprocess.run(["python3", "-I", "-c", editor[1], str(settings)],
                                    capture_output=True, text=True, check=True)
            after = json.loads(settings.read_text())
            assert after["lockPamPath"] == expected, (before, after)
            assert all(after[key] is True for key in flags), (before, after)
            assert after["other"] == 1, (before, after)
            custom = expected != MANAGED_LOCK
            assert custom == ("kept custom lockPamPath" in result.stderr), (before, result.stderr)
            if custom and before.keys() >= flags.keys():
                assert settings.read_text() == original, ("rewrote unchanged settings", before)
    print("PASS: installer settings: managed lock stack selected, custom lockPamPath preserved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pam-root", type=Path, default=Path(__file__).resolve().parents[1] / "system/pam.d")
    args = parser.parse_args()
    pam = ctypes.CDLL("libpam.so.0")
    conversation = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

    class Conversation(ctypes.Structure):
        _fields_ = [("callback", conversation), ("data", ctypes.c_void_p)]

    @conversation
    def unexpected_prompt(count, messages, responses, data):
        return 19  # PAM_CONV_ERR: simulated modules should never prompt.

    conv = Conversation(unexpected_prompt, None)
    pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
    with tempfile.TemporaryDirectory(prefix="howdy-pam-check-") as directory:
        root = Path(directory)
        trace = root / "trace"
        module = root / "module.sh"
        # "stall" stands in for a camera that never returns.
        module.write_text('#!/bin/sh\nprintf "%s\\n" "$2" >> "$1"\n[ "$3" = stall ] && { sleep 20; exit 1; }\nexit "$3"\n')
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
    check_settings_editor()


if __name__ == "__main__":
    main()
