#!/usr/bin/env python3
"""Check the real PAM bridge with dummy secrets, including a real TPM round-trip.

Run as root. No enrolled credential, wallet, camera or live PAM file is used.
An additional build changes only the decrypt executable to exercise malformed
output and timeout recovery without stalling the physical TPM.
--decrypt-stub-only runs just that substituted-decrypt part: it needs no TPM or
built module and works as root in a user namespace (`unshare -r`).
"""

import argparse
import ctypes
import importlib.util
import os
from pathlib import Path
import pwd
import signal
import subprocess
import tempfile
import time
from unittest.mock import patch

OBSERVER = r'''
#include <security/pam_modules.h>
#include <stdio.h>
#include <string.h>
int pam_sm_authenticate(pam_handle_t *p, int f, int c, const char **v) {
    (void)f;
    if (c != 2) return PAM_SERVICE_ERR;
    unsigned char b[8192];
    FILE *in = fopen(v[1], "rb");
    if (!in) return PAM_SERVICE_ERR;
    size_t n = fread(b, 1, sizeof(b)-1, in);
    fclose(in); b[n] = 0;
    if (!strcmp(v[0], "set")) return pam_set_item(p, PAM_AUTHTOK, b);
    const void *token = NULL;
    int rc = pam_get_item(p, PAM_AUTHTOK, &token);
    if (rc != PAM_SUCCESS) return rc;
    const char *s = token ? token : "";
    return strlen(s) == n && !memcmp(s, b, n) ? PAM_SUCCESS : PAM_AUTH_ERR;
}
int pam_sm_setcred(pam_handle_t *p, int f, int c, const char **v) {
    (void)p; (void)f; (void)c; (void)v; return PAM_IGNORE;
}
'''

# Stand-in for systemd-creds. "signal" stalls where timeout(1) can stop it.
# "stuck" models a decrypt blocked in kernel I/O: a process timeout(1) cannot
# signal keeps the pipe open, so only the PAM caller's own deadline helps.
FAKE_DECRYPT = '''#!/usr/bin/python
import os, sys, time
from pathlib import Path
mode = os.environ.get("HOWDY_TEST_STALL")
if mode == "signal":
    time.sleep(60)
if mode == "stuck":
    if os.fork() == 0:
        os.setsid()
        Path(PIDFILE).write_text(str(os.getpid()))
        time.sleep(30)
        os._exit(0)
    sys.exit(0)
sys.stdout.buffer.write(Path(PAYLOAD).read_bytes())
'''


def compile_module(source, target):
    subprocess.run(["cc", "-D_GNU_SOURCE", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-o", str(target), str(source), "-lpam"], check=True, capture_output=True)


class Bridge:
    """Run one temporary PAM stack: optional prefix, the module, then an observer."""

    def __init__(self, root, credential):
        self.root, self.credential = root, credential
        self.pam = ctypes.CDLL("libpam.so.0")
        callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

        class Conversation(ctypes.Structure):
            _fields_ = [("callback", callback), ("data", ctypes.c_void_p)]

        self.refuse_prompt = callback(lambda n, messages, responses, data: 19)
        self.conv = Conversation(self.refuse_prompt, None)
        self.pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
        self.pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.expected = root / "expected"
        observer_source, self.observer = root / "observe.c", root / "observe.so"
        observer_source.write_text(OBSERVER)
        compile_module(observer_source, self.observer)

    def authenticate(self, expected_value, *, module, options=None, user="humunkulud", prefix="auth required pam_permit.so\n", observe=True):
        self.expected.write_bytes(expected_value)
        if options is None:
            options = f"user=humunkulud service=check cred={self.credential} name=howdy-test"
        lines = prefix + f"auth optional {module.resolve()} {options}\n"
        if observe:
            lines += f"auth required {self.observer} check {self.expected}\n"
        (self.root / "check").write_text(lines)
        handle = ctypes.c_void_p()
        status = self.pam.pam_start_confdir(b"check", user.encode(), ctypes.byref(self.conv), str(self.root).encode(), ctypes.byref(handle))
        assert status == 0, ("pam_start_confdir", status)
        try:
            status = self.pam.pam_authenticate(handle, 0)
        finally:
            self.pam.pam_end(handle, status)
        return status == 0


def check_real_tpm(module, root, secret, credential, bridge):
    subprocess.run(["systemd-creds", "encrypt", "--with-key=host+tpm2", "--tpm2-pcrs=7", "--name=howdy-test", "-", str(credential)], input=secret, check=True, capture_output=True, timeout=15)
    credential.chmod(0o600)
    recovered = subprocess.run(["systemd-creds", "decrypt", "--no-ask-password", "--name=howdy-test", str(credential), "-"], check=True, capture_output=True, timeout=15)
    assert recovered.stdout == secret, "Real TPM round-trip differed"
    print("PASS: real host+TPM2/PCR7 credential round-trip")

    spec = importlib.util.spec_from_file_location("enrollment", Path(__file__).with_name("install-howdy-kwallet-tpm.py"))
    enrollment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(enrollment)
    original = credential.read_bytes()
    with patch.object(enrollment, "decrypt", return_value=b"incorrect dummy readback"):
        try:
            enrollment.seal(b"replacement-dummy", credential, "howdy-test")
        except ValueError:
            pass
        else:
            raise AssertionError("Mismatched enrollment readback was accepted")
    assert credential.read_bytes() == original, "Failed enrollment replaced the existing credential"
    assert not list(root.glob(".enroll-*")), "Failed enrollment left a temporary credential"
    print("PASS: failed enrollment preserves the old credential and cleans up")

    def authenticate(expected_value, **kwargs):
        return bridge.authenticate(expected_value, module=module, **kwargs)

    typed = root / "typed"
    typed.write_bytes(b"dummy-typed-password")
    assert authenticate(secret), "Real bridge failed to supply the sealed dummy token"
    assert authenticate(b"dummy-typed-password", prefix=f"auth required {bridge.observer} set {typed}\n"), "Typed token was overwritten"
    assert authenticate(b"", user="another-local-account"), "Credential reached another PAM user"
    assert authenticate(b"", options=f"user=humunkulud service=wrong cred={credential} name=howdy-test"), "Credential reached another PAM service"
    assert authenticate(b"", options=f"cred={credential} name=howdy-test"), "Unscoped module released a token"
    assert not authenticate(b"", prefix="", observe=False), "Token supplier authenticated on its own"
    assert not authenticate(secret, prefix="auth requisite pam_deny.so\n"), "Token supplier bypassed denied authentication"
    credential.chmod(0o644)
    assert authenticate(b""), "Public credential accepted"
    credential.chmod(0o600)
    os.chown(credential, pwd.getpwnam("nobody").pw_uid, -1)
    assert authenticate(b""), "Non-root credential accepted"
    os.chown(credential, 0, -1)
    assert authenticate(b"", options=f"user=humunkulud service=check cred={credential}.missing name=howdy-test"), "Missing credential did not degrade safely"
    assert authenticate(b"", options=f"user=humunkulud service=check cred={credential} name=wrong-name"), "Wrong credential name accepted"
    print("PASS: real PAM token delivery, account/service scope, typed-token preservation, permissions and failure fallback")


def check_decrypt_stub(source, root, bridge):
    # Substitute only the external decrypt operation for bounded failure tests.
    fake = root / "dummy-decrypt"
    payload = root / "payload"
    pidfile = root / "stuck.pid"
    fake.write_text(FAKE_DECRYPT.replace("PAYLOAD", repr(str(payload))).replace("PIDFILE", repr(str(pidfile))))
    fake.chmod(0o700)
    src = source.read_text()
    marker = '#define SYSTEMD_CREDS "/usr/bin/systemd-creds"'
    assert src.count(marker) == 1
    fake_source, fake_module = root / "mock.c", root / "mock.so"
    fake_source.write_text(src.replace(marker, '#define SYSTEMD_CREDS "' + str(fake) + '"'))
    compile_module(fake_source, fake_module)
    for value, result in ((b"", b""), (b"\0bad", b""), (b"x" * 4097, b""), (b"x" * 4096, b"x" * 4096), (b"dummy\n", b"dummy")):
        payload.write_bytes(value)
        assert bridge.authenticate(result, module=fake_module), "Malformed output handling failed"
    print("PASS: malformed/oversized output rejected")

    for mode, limit in (("signal", 7), ("stuck", 8.5)):
        os.environ["HOWDY_TEST_STALL"] = mode
        start = time.monotonic()
        try:
            assert bridge.authenticate(b"", module=fake_module), f"Stalled ({mode}) decrypt blocked fallback"
        finally:
            os.environ.pop("HOWDY_TEST_STALL", None)
            if pidfile.exists():
                try:
                    os.kill(int(pidfile.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
                pidfile.unlink()
        elapsed = time.monotonic() - start
        assert elapsed < limit, f"Decrypt deadline was not enforced ({mode}): {elapsed:.1f}s"
        print(f"PASS: {mode} decrypt stall returned without a token after {elapsed:.1f}s (limit {limit}s)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, help="Built module; required unless --decrypt-stub-only")
    parser.add_argument("--source", type=Path, required=True, help="Patched upstream C source")
    parser.add_argument("--decrypt-stub-only", action="store_true", help="Skip the real TPM and built module")
    args = parser.parse_args()
    if not args.module and not args.decrypt_stub_only:
        parser.error("--module is required unless --decrypt-stub-only")
    if os.geteuid() != 0:
        parser.error("Run through sudo (or `unshare -r` with --decrypt-stub-only); the module requires root-owned fixtures")

    with tempfile.TemporaryDirectory(prefix="howdy-tpm-check-") as directory:
        root = Path(directory)
        secret = b"dummy-TPM-password-" + os.urandom(16).hex().encode()
        credential = root / "test.cred"
        bridge = Bridge(root, credential)
        if args.decrypt_stub_only:
            credential.write_bytes(b"not a real credential")
            credential.chmod(0o600)
        else:
            check_real_tpm(args.module, root, secret, credential, bridge)
        check_decrypt_stub(args.source, root, bridge)


if __name__ == "__main__":
    main()
