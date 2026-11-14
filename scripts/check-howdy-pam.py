#!/usr/bin/env python3
"""Exercise managed auth control flow with real libpam and simulated auth results.

No camera, passwords, root privileges or live PAM changes are needed. pam_exec
records which modules libpam reaches, substituting only the module operation.
"""

import argparse
import ctypes
from pathlib import Path
import re
import tempfile


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
        module.write_text('#!/bin/sh\nprintf "%s\\n" "$2" >> "$1"\nexit "$3"\n')
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
                    stack.append(f"{kind} {control} pam_exec.so quiet /bin/sh {module} {trace} {name} {0 if result else 1}")
                (root / "check").write_text("\n".join(stack) + "\n")
                handle = ctypes.c_void_p()
                result = pam.pam_start_confdir(b"check", b"howdy-test", ctypes.byref(conv), str(root).encode(), ctypes.byref(handle))
                assert result == 0, ("pam_start_confdir", result)
                try:
                    result = pam.pam_authenticate(handle, 0)
                finally:
                    pam.pam_end(handle, result)
                return result == 0, trace.read_text().splitlines()

            for face, password, expected in ((True, False, True), (False, True, True), (False, False, False)):
                success, reached = authenticate(face, password)
                assert success == expected, (service, face, password, success, reached)
                methods = [name for name in reached if name in ("pam_howdy.so", "pam_unix.so")]
                assert methods == (["pam_howdy.so"] if face else ["pam_howdy.so", "pam_unix.so"]), (service, methods)
                if expected:
                    continuation = "pam_kwallet5.so" if service == "greetd" else "pam_env.so"
                    assert continuation in reached, (service, "skipped continuation", reached)
            # A successful face cannot bypass existing prerequisite failures.
            guards = ("pam_securetty.so", "pam_nologin.so") if service == "greetd" else ("pam_nologin.so", "pam_shells.so")
            for guard in guards:
                success, reached = authenticate(True, False, guard)
                assert not success, (service, "bypassed guard", guard, reached)
            print(f"PASS: {service}: face first, password fallback, deny both failures, continuation and prerequisite guards")


if __name__ == "__main__":
    main()
