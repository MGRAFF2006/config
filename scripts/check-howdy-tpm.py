#!/usr/bin/env python3
"""Check the real PAM bridge with dummy secrets, including a real TPM round-trip.

Run as root. No enrolled credential, wallet, camera or live PAM file is used.
An additional build changes only the decrypt executable to exercise malformed
output and timeout recovery without stalling the physical TPM.
"""

import argparse
import ctypes
import importlib.util
import os
from pathlib import Path
import pwd
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True, help="Patched upstream C source")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Run through sudo; fixtures must be root-owned for the real module")
    pam = ctypes.CDLL("libpam.so.0")
    callback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)

    class Conversation(ctypes.Structure):
        _fields_ = [("callback", callback), ("data", ctypes.c_void_p)]

    @callback
    def refuse_prompt(n, messages, responses, data):
        return 19

    conv = Conversation(refuse_prompt, None)
    pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
    pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
    pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]

    def compile_module(source, target):
        subprocess.run(["cc", "-D_GNU_SOURCE", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC", "-o", str(target), str(source), "-lpam"], check=True, capture_output=True)

    with tempfile.TemporaryDirectory(prefix="howdy-tpm-check-") as directory:
        root = Path(directory)
        secret = b"dummy-TPM-password-" + os.urandom(16).hex().encode()
        credential = root / "test.cred"
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

        expected = root / "expected"
        typed = root / "typed"
        typed.write_bytes(b"dummy-typed-password")
        observer_source, observer = root / "observe.c", root / "observe.so"
        observer_source.write_text(OBSERVER)
        compile_module(observer_source, observer)

        def authenticate(expected_value, *, module=args.module, options=None, user="humunkulud", prefix="auth required pam_permit.so\n", observe=True):
            expected.write_bytes(expected_value)
            if options is None:
                options = f"user=humunkulud service=check cred={credential} name=howdy-test"
            lines = prefix + f"auth optional {module.resolve()} {options}\n"
            if observe:
                lines += f"auth required {observer} check {expected}\n"
            (root / "check").write_text(lines)
            handle = ctypes.c_void_p()
            status = pam.pam_start_confdir(b"check", user.encode(), ctypes.byref(conv), str(root).encode(), ctypes.byref(handle))
            assert status == 0, ("pam_start_confdir", status)
            try:
                status = pam.pam_authenticate(handle, 0)
            finally:
                pam.pam_end(handle, status)
            return status == 0

        assert authenticate(secret), "Real bridge failed to supply the sealed dummy token"
        assert authenticate(b"dummy-typed-password", prefix=f"auth required {observer} set {typed}\n"), "Typed token was overwritten"
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

        # Substitute only the external decrypt operation for bounded failure tests.
        fake = root / "dummy-decrypt"
        payload = root / "payload"
        fake.write_text("#!/usr/bin/python\nimport os,time,sys\nfrom pathlib import Path\nif os.environ.get('HOWDY_TEST_STALL'): time.sleep(60)\nsys.stdout.buffer.write(Path(" + repr(str(payload)) + ").read_bytes())\n")
        fake.chmod(0o700)
        src = args.source.read_text()
        marker = '#define SYSTEMD_CREDS "/usr/bin/systemd-creds"'
        assert src.count(marker) == 1
        fake_source, fake_module = root / "mock.c", root / "mock.so"
        fake_source.write_text(src.replace(marker, '#define SYSTEMD_CREDS "' + str(fake) + '"'))
        compile_module(fake_source, fake_module)
        for value, result in ((b"", b""), (b"\0bad", b""), (b"x" * 4097, b""), (b"x" * 4096, b"x" * 4096), (b"dummy\n", b"dummy")):
            payload.write_bytes(value)
            assert authenticate(result, module=fake_module), "Malformed output handling failed"
        os.environ["HOWDY_TEST_STALL"] = "1"
        start = time.monotonic()
        try:
            assert authenticate(b"", module=fake_module), "Stalled decrypt blocked fallback"
        finally:
            os.environ.pop("HOWDY_TEST_STALL", None)
        elapsed = time.monotonic() - start
        assert elapsed < 7, f"Decrypt deadline was not enforced: {elapsed:.1f}s"
        print("PASS: malformed/oversized output rejected; stalled decrypt returned within 7 seconds")


if __name__ == "__main__":
    main()
