# KWallet after face login

This local package pins [howdy-tpm](https://github.com/jibsta210/howdy-tpm) at
`6483553f7f7b163b5790f9c763f6fa1e08624ddd`. It supplies `PAM_AUTHTOK` only after
the managed greetd stack has authenticated, so the existing KWallet PAM module
can follow its normal password-unlock path. It never authenticates a user itself.

The hardening patch requires an explicit matching PAM account and service,
preserves typed passwords, bounds unsealing to five seconds plus a one-second
kill deadline, and rejects unsafe or malformed credentials. Only the module is
installed; upstream's enrollment and automatic PAM detection are not used.

```bash
cd ~/Documents/config/packages/aur-builds/howdy-tpm
makepkg
sudo pacman -U ./howdy-tpm-0.1.r6.g6483553-1-x86_64.pkg.tar.zst
cd ~/Documents/config
sudo python scripts/install-howdy-kwallet-tpm.py --user humunkulud --apply
sudo python scripts/install-howdy-kwallet-tpm.py --user humunkulud --check
```

Enrollment prompts invisibly for the existing wallet password. It seals to
`/etc/howdy-tpm/humunkulud.cred`, root-owned mode 0600, using systemd's host key,
the local TPM2, and PCR 7. The secret never appears in arguments or source files.
A private runtime secret file is also supported for the agent's secret-input
facility; it must be a regular owner-only file of the selected account and is
read through one validated, no-follow descriptor, at most 4096 bytes. Exact
readback is verified before atomic replacement. A failed enrollment leaves
greetd PAM untouched and restores only a credential it already replaced; old
ciphertext and PAM files are retained under `/var/backups/howdy-kwallet-tpm/`.

This keeps the wallet encrypted. It does not make software face recognition a
hardware-verified authenticator. With the laptop's current unencrypted disk and
disabled Secure Boot, a modified OS booted on this same laptop can recover the
sealed password. PCR 7 alone does not establish a trusted boot chain in that
configuration. Treat enrollment as a convenience tradeoff unless boot and
storage protection have first been established. It protects against copying the
encrypted credential to another machine, not an already compromised root.

Firmware/TPM/Secure Boot changes may stop automatic unsealing. The original
wallet password continues to work, and the bridge is optional: missing files,
an unavailable TPM or module failure leave login and manual wallet unlocking
available. Re-enroll after password changes. Do not reset the wallet or forget
its original password.

To disable without deleting anything, move the credential aside:

```bash
sudo mv /etc/howdy-tpm/humunkulud.cred /etc/howdy-tpm/humunkulud.cred.disabled
```

The lock and sudo stacks do not receive this password. Separate app vaults such
as Bitwarden retain their own unlock policy. Face-first polkit is configured
separately through `scripts/install-howdy-polkit.py`, with no TPM secret there.

Verification uses a dummy secret and temporary PAM stacks:

```bash
sudo python scripts/check-howdy-tpm.py \
  --module packages/aur-builds/howdy-tpm/src/howdy-tpm-6483553f7f7b163b5790f9c763f6fa1e08624ddd/pam_howdy_tpm.so \
  --source packages/aur-builds/howdy-tpm/src/howdy-tpm-6483553f7f7b163b5790f9c763f6fa1e08624ddd/src/pam_howdy_tpm.c
python scripts/check-howdy-kwallet-enroll.py
python scripts/check-howdy-polkit.py
sudo python scripts/check-howdy-polkit.py --sandbox --user humunkulud
```

These checks never use the enrolled credential or capture camera frames.
