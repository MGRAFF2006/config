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


def command(arguments, **kwargs):
    return subprocess.run(arguments, check=True, timeout=15, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, **kwargs)


def decrypt(path, name):
    return command(["systemd-creds", "decrypt", "--no-ask-password",
                    f"--name={name}", str(path), "-"]).stdout


def private_file(path, owner):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != owner or info.st_mode & 0o077:
        raise ValueError(f"Expected an owner-only regular file: {path}")


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
        private_file(args.secret_file, account.pw_uid)
        password = args.secret_file.read_bytes()
    else:
        password = getpass.getpass("Existing KWallet/login password: ").encode()
        if not hmac.compare_digest(password, getpass.getpass("Again: ").encode()):
            raise ValueError("Passwords do not match")
    if not password or len(password) > 4096 or b"\0" in password or b"\n" in password:
        raise ValueError("Expected a nonempty single-line password, at most 4096 bytes")

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = Path("/var/backups/howdy-kwallet-tpm") / stamp
    backup.mkdir(parents=True, mode=0o700)
    # Preserve the old credential and PAM before either replacement.
    shutil.copy2(PAM, backup / "greetd")
    existed = target.exists()
    if existed:
        private_file(target, 0)
        shutil.copy2(target, backup / target.name)
    changed = False
    try:
        seal(password, target, name)
        changed = True
        fd, temporary = tempfile.mkstemp(prefix=".greetd-howdy-", dir=PAM.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(source)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o644)
            os.replace(temporary, PAM)
        finally:
            Path(temporary).unlink(missing_ok=True)
    except BaseException:
        if changed:
            if existed:
                shutil.copy2(backup / target.name, target)
            else:
                target.unlink(missing_ok=True)
        shutil.copy2(backup / "greetd", PAM)
        raise
    print(f"Installed account-bound KWallet handoff; backups: {backup}")
    print("Applies at your next normal login. Manual wallet/password fallback remains available.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        # SubprocessError string contains the command but never the password input.
        raise SystemExit(f"KWallet TPM setup failed: {error}") from None
