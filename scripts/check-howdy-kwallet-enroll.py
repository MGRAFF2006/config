#!/usr/bin/env python3
"""Check KWallet TPM enrollment input and rollback with temporary fixtures.

No TPM, wallet, real password or live PAM file is used: systemd-creds is
replaced by an in-process stub and every path points into a temporary
directory. Runs as root inside a user namespace (re-executes through
`unshare -r` when started unprivileged) so the root-ownership checks are real.
"""

import importlib.util
import itertools
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_installer():
    spec = importlib.util.spec_from_file_location("enrollment", ROOT / "scripts/install-howdy-kwallet-tpm.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rejected(function, *args):
    try:
        function(*args)
    except (OSError, ValueError):
        return True
    return False


def check_secret_file(enrollment, root):
    owner = os.getuid()
    secret = root / "secret"
    victim = root / "victim"
    victim.write_bytes(b"not-the-users-secret")
    victim.chmod(0o644)

    secret.write_bytes(b"dummy-wallet-password")
    secret.chmod(0o600)
    assert enrollment.read_secret_file(secret, owner) == b"dummy-wallet-password"
    assert rejected(enrollment.read_secret_file, secret, owner + 1), "Another owner's file accepted"
    secret.chmod(0o640)
    assert rejected(enrollment.read_secret_file, secret, owner), "Group-readable secret accepted"
    secret.chmod(0o600)

    link = root / "link"
    link.symlink_to(secret)
    assert rejected(enrollment.read_secret_file, link, owner), "Symlinked secret accepted"

    fifo = root / "fifo"
    os.mkfifo(fifo, 0o600)
    signal.alarm(5)  # A blocking open/read on a FIFO would hang here.
    try:
        assert rejected(enrollment.read_secret_file, fifo, owner), "FIFO accepted"
    finally:
        signal.alarm(0)

    # Swap the pathname after the precheck: the descriptor actually read must
    # be validated, so neither a symlink nor a public file can slip through.
    real_lstat = os.lstat

    def swapping_lstat(replacement):
        def lstat(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if Path(path) == secret:
                staged = root / "staged"
                replacement(staged)
                os.replace(staged, secret)
            return info
        return lstat

    for name, replacement in (("symlink", lambda path: path.symlink_to(victim)),
                              ("public file", lambda path: (path.write_bytes(victim.read_bytes()), path.chmod(0o644)))):
        secret.unlink()
        secret.write_bytes(b"dummy-wallet-password")
        secret.chmod(0o600)
        with patch.object(enrollment.os, "lstat", swapping_lstat(replacement)):
            try:
                value = enrollment.read_secret_file(secret, owner)
            except (OSError, ValueError):
                value = None
        assert value is None, f"Swapped {name} was read: {value!r}"

    secret.unlink()
    with secret.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024)  # Sparse; an unbounded read would load it all.
    secret.chmod(0o600)
    real_read = os.read
    total = []

    def counting_read(fd, size):
        data = real_read(fd, size)
        total.append(len(data))
        return data

    with patch.object(enrollment.os, "read", counting_read):
        assert rejected(enrollment.read_secret_file, secret, owner), "Oversized secret accepted"
    assert sum(total) <= enrollment.MAX_PASSWORD + 1, f"Read {sum(total)} bytes of an oversized secret"
    secret.write_bytes(b"x" * enrollment.MAX_PASSWORD)
    assert len(enrollment.read_secret_file(secret, owner)) == enrollment.MAX_PASSWORD
    print("PASS: secret file read through a validated, bounded, no-follow descriptor")


def fingerprint(path):
    info = os.lstat(path)
    return info.st_ino, info.st_mode, info.st_mtime_ns, info.st_ctime_ns, path.read_bytes()


def check_enrollment(enrollment, root):
    pam = root / "pam.d" / "greetd"
    store = root / "howdy-tpm"
    pam.parent.mkdir()
    store.mkdir(mode=0o700)
    target = store / "user.cred"
    attempts = itertools.count()

    def fake_command(arguments, **kwargs):
        # Stand-in for `systemd-creds encrypt ... - <output>`; records the input.
        if fake_command.fail:
            raise subprocess.CalledProcessError(1, arguments[:2])
        Path(arguments[-1]).write_bytes(b"sealed:" + kwargs["input"])
        return subprocess.CompletedProcess(arguments, 0, b"", b"")

    def fake_decrypt(path, name):
        return Path(path).read_bytes().removeprefix(b"sealed:") if not fake_decrypt.mismatch else b"wrong"

    real_install = enrollment.atomic_install

    def failing_pam_install(content, path, mode):
        if path == pam:
            raise OSError("simulated PAM write failure")
        return real_install(content, path, mode)

    def run(previous, *, seal_fails=False, mismatch=False, pam_fails=False):
        pam.write_bytes(b"old managed pam\n")
        pam.chmod(0o644)
        target.unlink(missing_ok=True)
        if previous is not None:
            target.write_bytes(previous)
            target.chmod(0o600)
        before_pam = fingerprint(pam)
        before_target = fingerprint(target) if previous is not None else None
        time.sleep(0.02)  # Any write would now move the change time.
        fake_command.fail, fake_decrypt.mismatch = seal_fails, mismatch
        backup = root / "backups" / str(next(attempts))
        with patch.object(enrollment, "PAM", pam), patch.object(enrollment, "command", fake_command), \
                patch.object(enrollment, "decrypt", fake_decrypt), \
                patch.object(enrollment, "atomic_install", failing_pam_install if pam_fails else real_install):
            try:
                enrollment.enroll(b"new-dummy-password", target, "test", b"new managed pam\n", backup)
            except (OSError, ValueError, subprocess.CalledProcessError):
                failed = True
            else:
                failed = False
        assert not list(store.glob(".*")) and not list(pam.parent.glob(".*")), "Temporary file left behind"
        assert (backup / "greetd").read_bytes() == b"old managed pam\n"
        return failed, before_pam, before_target

    for previous in (None, b"sealed:old-dummy-password"):
        for seal_fails, mismatch in ((True, False), (False, True)):
            failed, before_pam, before_target = run(previous, seal_fails=seal_fails, mismatch=mismatch)
            assert failed, "Seal failure was hidden"
            assert fingerprint(pam) == before_pam, "PAM was written although nothing was replaced"
            if previous is None:
                assert not target.exists(), "Failed enrollment created a credential"
            else:
                assert fingerprint(target) == before_target, "Failed enrollment touched the old credential"

        failed, before_pam, _ = run(previous, pam_fails=True)
        assert failed, "PAM failure was hidden"
        assert fingerprint(pam) == before_pam, "PAM changed although its replacement failed"
        if previous is None:
            assert not target.exists(), "New credential kept after PAM failure"
        else:
            assert target.read_bytes() == previous and target.stat().st_mode & 0o777 == 0o600, \
                "Old credential not restored after PAM failure"
            assert target.stat().st_uid == 0

        failed, _, _ = run(previous)
        assert not failed, "Successful enrollment failed"
        assert pam.read_bytes() == b"new managed pam\n" and pam.stat().st_mode & 0o777 == 0o644
        assert target.read_bytes() == b"sealed:new-dummy-password" and target.stat().st_mode & 0o777 == 0o600
    print("PASS: enrollment leaves PAM untouched on seal failure and restores only replaced files")


def main():
    if os.geteuid() != 0:
        os.execvp("unshare", ["unshare", "-r", sys.executable, *sys.argv])
    enrollment = load_installer()
    with tempfile.TemporaryDirectory(prefix="howdy-kwallet-enroll-check-") as directory:
        root = Path(directory)
        check_secret_file(enrollment, root)
        check_enrollment(enrollment, root)


if __name__ == "__main__":
    main()
