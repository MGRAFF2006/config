#!/usr/bin/env python3
"""Enroll a TPM-protected KWallet password and install the managed greetd stack.

Only encrypted credentials are saved. Existing wallet/password authentication
is unchanged. This does not restart the display manager or the desktop.
"""

import argparse
from datetime import datetime
import getpass
import hmac
import os
from pathlib import Path
import pwd
import shutil
import stat
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STORE = Path("/etc/howdy-tpm")
PAM = Path("/etc/pam.d/greetd")
MODULE = Path("/usr/lib/security/pam_howdy_tpm.so")
MAX_PASSWORD = 4096


def command(arguments, **kwargs):
    return subprocess.run(arguments, check=True, timeout=15, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kwargs)


def decrypt(path, name):
    return command(["systemd-creds", "decrypt", "--no-ask-password",
                    f"--name={name}", str(path), "-"]).stdout


def check_private(info, owner, path):
    if not stat.S_ISREG(info.st_mode) or info.st_uid != owner or info.st_mode & 0o077:
        raise ValueError(f"Expected an owner-only regular file: {path}")


def private_file(path, owner):
    check_private(os.lstat(path), owner, path)


def read_secret_file(path, owner):
    """Read a user-supplied secret through one validated, bounded descriptor.

    The pathname is user-controlled, so it may change between checks. The
    pathname precheck only avoids opening devices or FIFOs; the decision uses
    the descriptor that is actually read.
    """
    private_file(path, owner)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC)
    try:
        check_private(os.fstat(fd), owner, path)
        data = b""
        while len(data) <= MAX_PASSWORD:
            chunk = os.read(fd, MAX_PASSWORD + 1 - len(data))
            if not chunk:
                break
            data += chunk
    finally:
        os.close(fd)
    if len(data) > MAX_PASSWORD:
        raise ValueError(f"Secret file exceeds {MAX_PASSWORD} bytes")
    return data


def atomic_install(content, path, mode):
    """Replace path in one rename; on failure the original stays untouched."""
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def seal(password, target, name):
    """Verify exact round-trip before atomically replacing a credential."""
    fd, temporary = tempfile.mkstemp(prefix=".enroll-", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        command(["systemd-creds", "encrypt", "--with-key=host+tpm2", "--tpm2-pcrs=7",
                 f"--name={name}", "-", str(temporary)], input=password)
        os.chmod(temporary, 0o600)
        private_file(temporary, 0)
        if not hmac.compare_digest(decrypt(temporary, name), password):
            raise ValueError("TPM credential round-trip did not match; nothing replaced")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def enroll(password, target, name, source, backup):
    """Replace the credential, then greetd PAM; undo only what was replaced."""
    backup.mkdir(parents=True, mode=0o700)
    # Preserve the old credential and PAM before either replacement.
    shutil.copy2(PAM, backup / PAM.name)
    previous = None
    if target.exists():
        private_file(target, 0)
        previous = target.read_bytes()
        shutil.copy2(target, backup / target.name)
    # seal() verifies the readback before its atomic rename; a failure there
    # leaves both the credential and PAM untouched.
    seal(password, target, name)
    try:
        atomic_install(source, PAM, 0o644)
    except BaseException:
        # PAM replacement is a single rename, so only the credential changed.
        if previous is None:
            target.unlink(missing_ok=True)
        else:
            atomic_install(previous, target, 0o600)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default=os.environ.get("SUDO_USER", getpass.getuser()))
    parser.add_argument("--secret-file", type=Path, help="Private runtime secret input; never copied to disk")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    account = pwd.getpwnam(args.user)
    if account.pw_uid == 0:
        parser.error("Select the desktop account with --user")
    source = (ROOT / "system/pam.d/greetd").read_bytes()
    target = STORE / f"{account.pw_name}.cred"
    name = f"howdy-kwallet-{account.pw_name}"
    expected = f"pam_howdy_tpm.so user={account.pw_name} service=greetd cred={target} name={name}"
    if expected.encode() not in source:
        parser.error("Managed greetd stack does not match the requested account/credential")
    if not args.apply and not args.check:
        print(f"Plan: enroll host+TPM2 credential {target}, bound to PCR 7; install {PAM}")
        print("Requires the local howdy-tpm package. Use --apply; no services are restarted.")
        return
    if os.geteuid() != 0:
        parser.error("Run --apply/--check through sudo")
    if not MODULE.is_file():
        parser.error("Install the local packages/aur-builds/howdy-tpm package first")
    command(["systemd-analyze", "has-tpm2"])
    if args.check:
        private_file(target, 0)
        if not decrypt(target, name):
            raise ValueError("The enrolled credential is empty")
        if PAM.read_bytes() != source:
            raise ValueError("Live greetd PAM differs from the managed source")
        print("PASS: account-bound credential unseals; installed greetd matches the source")
        return

    os.umask(0o077)
    if STORE.exists():
        info = STORE.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o077:
            raise ValueError("Credential directory must be root-owned mode 0700")
    else:
        STORE.mkdir(mode=0o700)
    if args.secret_file:
        password = read_secret_file(args.secret_file, account.pw_uid)
    else:
        password = getpass.getpass("Existing KWallet/login password: ").encode()
        if not hmac.compare_digest(password, getpass.getpass("Again: ").encode()):
            raise ValueError("Passwords do not match")
    if not password or len(password) > MAX_PASSWORD or b"\0" in password or b"\n" in password:
        raise ValueError(f"Expected a nonempty single-line password, at most {MAX_PASSWORD} bytes")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = Path("/var/backups/howdy-kwallet-tpm") / stamp
    enroll(password, target, name, source, backup)
    print(f"Installed account-bound KWallet handoff; backups: {backup}")
    print("Applies at your next normal login. Manual wallet/password fallback remains available.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # SubprocessError string contains the command but never the password input.
        raise SystemExit(f"KWallet TPM setup failed: {error}") from None
