# Laptop boot/storage protection before wallet auto-unlock

Verified 2026-11-15 on `laptop`; preparation only. Mathis chose protected boot
and storage before saving a TPM-unlocked copy of the login/KWallet password.
The [prepared wallet integration](https://github.com/MGRAFF2006/config/pull/38)
is not installed or enrolled. Existing Howdy login/lock remains unchanged.

## Current state

- Lenovo IdeaPad Slim 5 14AKP10, firmware R0CN22WW; TPM2 works.
- Secure Boot is off and firmware Setup Mode is off; PK/KEK are enrolled.
- Current kernel/boot images: 7.3.4-arch1-1. Installed GRUB 2.16, mkinitcpio
  42.2, systemd 262.2 and cryptsetup 2.8.8. Recheck versions before migration.
- One approximately 1 TB NVMe. Partition 1 is a 1 GiB FAT ESP mounted at `/boot`
  with about 911 MiB available. Partition 2 is an unencrypted Btrfs filesystem,
  about 953 GiB total with 796 GiB used and 152 GiB free when checked.
- Btrfs subvolumes: `@`, `@home`, `@log`, `@pkg`, and nested
  `@/var/lib/portables` and `@/var/lib/machines`. Backup/restore must account
  for all six; root snapshots alone omit nested subvolume contents.
- Only about 1 MiB is currently unallocated at the block-device level. The
  filesystem's reported free space is inside allocated chunks; it does not
  establish unused tail space for an in-place LUKS header.
- Current initramfs uses `udev`, without `encrypt`/`sd-encrypt`. There is only a
  default image, no configured fallback preset or UKI. Systemd's EFI stub is
  installed; `ukify` and `sbctl` are not.

## Proposed end state

Use LUKS2 around the entire existing Btrfs system partition, preserving the
installation, applications and subvolume topology through backup/restore.
Keep the ESP outside LUKS and authenticate its boot payloads with signed UKIs
containing kernel, initramfs and command line. Prefer systemd-boot and a normal
plus recovery UKI over extending the current GRUB Secure Boot configuration.
The existing ESP appears large enough, but measure the built images first.

Use the native systemd initramfs/`sd-encrypt` path. Mkinitcpio supports UKI
output; a signed UKI covers the payloads that a separately signed kernel leaves
outside its signature. Verify embedded command-line behavior and update hooks
before enabling Secure Boot. See [mkinitcpio](https://man.archlinux.org/man/mkinitcpio.8)
and [systemd-stub](https://www.freedesktop.org/software/systemd/man/latest/systemd-stub.html).

Keep a working manual LUKS passphrase and off-device recovery material before
adding TPM automatic disk unlock. Bind later TPM release to authenticated boot
and the trusted UKI; signed PCR policies can support reviewed kernel updates.
The wallet bridge's PCR 7 binding alone is not a substitute for this protected
root and boot chain. See [systemd-cryptenroll](https://www.freedesktop.org/software/systemd/man/latest/systemd-cryptenroll.html).

## Backup and recovery prerequisites

The existing `homelab-backup-copy` job copies homelab application backups TO the
laptop. It is not a laptop backup. No verified full laptop backup was found.

`root@homelab-pve`'s ZFS mirror `bulk` reports about 1.87 TiB available. This is
a candidate for a dedicated encrypted laptop backup, with a quota and reserved
headroom. Verify source logical size and retention needs before allocating it.
Keep this separate from the services VM's data disk, which is itself included
in VM backups. No backup dataset/repository has been created by this task.

Before disk or firmware changes:

1. Back up the recoverable installation, all six subvolumes, ESP, partition
   table and relevant metadata to the off-laptop target. Preserve owner IDs,
   ACLs, extended attributes, links and boot configuration. Same-disk snapshots
   do not replace the off-device backup. List the subvolumes in the final
   backup and match them against `btrfs subvolume list /`; all six must be
   present and non-empty where the source is.
2. Verify the backup and restore representative data, including dirty project
   work and account configuration, without exposing credentials in logs/Git.
   Keep the backup password and homelab access credentials recoverable without
   this laptop, for example in Bitwarden.
3. Prove the complete restore fits before anything is erased. A representative
   restore is not enough. The target is the final LUKS mapping: partition 2
   minus the LUKS2 header (16 MiB by default), with at least 10% kept free.
   Use one of these:
   - Preferred: a full trial restore of all six subvolumes onto encrypted
     scratch storage on the homelab, such as a zvol in an encrypted ZFS
     dataset or a LUKS2 container on a zvol. Never use an unencrypted zvol,
     image or directory: it would leave a second plaintext copy of the
     installation. Size it exactly like the final mapping, use the same
     `mkfs.btrfs` options, mount options (`compress=`) and restore commands
     as the real migration, then confirm every subvolume is complete and
     check `btrfs filesystem usage`. Destroy the scratch volume afterwards.
   - Otherwise: a conservative bound with no credit for compression or shared
     extents. Data is the sum of `du -sx --apparent-size` per subvolume
     (`-x` stops at nested subvolume boundaries, so each one is counted
     once). Metadata is twice the logical metadata used from
     `btrfs filesystem usage` (the default single-device profile is DUP),
     plus 1 GiB for system chunks and the global reserve. This bound holds
     for `rsync` and for `btrfs send` with or without compressed data.
   If neither shows a fit, reduce or exclude data deliberately before erasing.
4. Prepare a recovery path that does not depend on this laptop's ESP or boot
   manager. A recovery UKI on the same ESP is a convenience, not the
   independent path. Choose one:
   - Off-disk rescue media that the final Secure Boot policy accepts. Examples
     are shim-signed media when Microsoft's UEFI CA stays in `db`, or media
     whose EFI binaries are signed with the new owner key. The plain Arch ISO
     is unsigned, so it does not qualify.
   - A tested firmware rollback. Mathis, at the laptop, enters firmware setup
     with a known supervisor password, disables Secure Boot, boots the
     unsigned rescue media, and re-enables Secure Boot afterward.
   Mathis currently has neither a recovery USB nor an external backup disk.
   Homelab storage can replace the disk, but recovery boot remains an
   unresolved prerequisite.
5. Prove recovery before erasing. Boot this laptop from the exact rescue
   medium that will be used. With only tools on that medium and credentials
   available without the laptop, reach the backup, open the repository, and
   restore a sample: some files from each subvolume, a dirty project and the
   ESP. Compare checksums with the live system. Create a disposable LUKS2
   container (a file-backed loop device is enough) and unlock it by typing the
   passphrase. Reaching the backup over the network is not enough.
6. Arrange an AC-powered maintenance window and explicit reboot authorization,
   with Mathis present for firmware menus. Export current firmware trust data
   (`PK`, `KEK`, `db`, `dbx`) and preserve off-device LUKS/header/signing-key
   recovery material.

## Migration sequence and boundaries

After the verified backup, restore-fit proof and recovery proof, prefer creating
a fresh LUKS2 container and restoring the existing Btrfs installation into it.
That erases the current partition contents and therefore requires review of the
exact disk, restore evidence and explicit authorization before execution. No
such erase, partition, boot-order, firmware-key or reboot operation has been
performed.

`luksFormat` only writes a header and keyslots. It does not overwrite the data
area. A restore that never writes some sectors leaves the old plaintext in
them, readable from the raw device. Erase the old plaintext before
restoring, from the recovery path, within the same authorized erase.

First confirm the target: match the model and serial from `nvme list` to the
recorded laptop drive and check `nvme list-ns` shows a single namespace. Then
use the first supported method and verify that method, not another one.

1. NVMe sanitize: crypto erase, or block erase if crypto erase is unsupported.
   Check `sanicap` in `nvme id-ctrl`. Sanitize is device-wide and reaches
   spare or remapped flash that host writes cannot. Verify with
   `nvme sanitize-log`: the most recent sanitize status must be "completed
   successfully" and progress must be finished.
2. NVMe format with secure erase if sanitize is unsupported:
   `nvme format --ses=2` (crypto erase, if `fna` lists support) or `--ses=1`
   (user data erase); `--ses=0` erases nothing. `fna` also shows whether it
   covers all namespaces. `sanitize-log` says nothing about a format. Verify
   that this format command returned success and that `nvme id-ns` shows the
   expected LBA format.
3. Host overwrite of partition 2 through a throwaway random-key mapping, as in
   the
   [cryptsetup FAQ](https://gitlab.com/cryptsetup/cryptsetup/-/wikis/FrequentlyAskedQuestions),
   only if neither NVMe method is supported and Mathis explicitly accepts that
   old plaintext can survive in spare or remapped flash. Record that
   acceptance before running it. Verify that the write ended only at the end
   of the mapping ("No space left on device") with the full partition size
   written.

Sanitize and format also erase the ESP and partition table; recreate both and
restore the ESP from the backup. After any method, raw reads at several
offsets, including some within the old data range, are a spot check only.

Then create the partition layout and LUKS2 container, make the Btrfs filesystem,
and restore all six subvolumes as subvolumes, not plain directories. The new
filesystem and LUKS UUIDs differ from the old ones. Update `fstab`, the
`rd.luks` options and the UKI command line to match.

In-place encryption is technically possible but still requires a reliable
backup, a Btrfs shrink to create verified tail room, and an offline maintenance
boot for this root filesystem. It rewrites the device and complicates recovery;
free space alone is insufficient evidence. See the upstream
[Btrfs resize documentation](https://btrfs.readthedocs.io/en/latest/btrfs-filesystem.html)
and [cryptsetup reencryption manual](https://gitlab.com/cryptsetup/cryptsetup/-/raw/main/man/cryptsetup-reencrypt.8.adoc).

After restoring onto encrypted root, configure and test the initramfs/UKIs,
including recovery and update behavior. Generate persistent signing keys only
on protected storage. Enroll owner trust deliberately through the laptop's
firmware Setup Mode, retaining needed OEM/Microsoft trust; do not clear the TPM.
An unsigned old GRUB is not a usable fallback while Secure Boot is enabled.
See [sbctl's manual](https://man.archlinux.org/man/extra/sbctl/sbctl.8.en).

Sign every EFI binary the firmware can load: the systemd-boot binary
`EFI/systemd/systemd-bootx64.efi`, its fallback copy `EFI/BOOT/BOOTX64.EFI`,
and both UKIs. `bootctl install` and `update`, including the automatic
`systemd-boot-update.service`, copy `systemd-bootx64.efi.signed` when it exists
and otherwise fall back to the unsigned `.efi`. See
[bootctl's signed EFI files section](https://www.freedesktop.org/software/systemd/man/latest/bootctl.html).
So keep a signed `/usr/lib/systemd/boot/efi/systemd-bootx64.efi.signed`,
for example with `sbctl sign -s -o`, and have it re-signed whenever systemd
updates. After every systemd, kernel or initramfs update, and before
rebooting, verify every `.efi` file on the ESP with `sbctl verify` or
`sbverify --cert`. Remove any leftover unsigned loaders, or make sure no boot
entry points to one.

Those file checks only use the local signing certificate. Separately confirm
the firmware trusts it: read the live `db` (`mokutil --db` or
`efi-readvar -v db`) and match the signing certificate's fingerprint
(`openssl x509 -fingerprint`). Repeat after firmware updates or key changes.

With Secure Boot enforced (`bootctl status`), boot each path once: the normal
UKI, the fallback `EFI/BOOT/BOOTX64.EFI` (select the disk itself in the
firmware boot menu), the recovery UKI and the independent recovery path.
From the recovery path, unlock the actual LUKS volume manually with the
passphrase and with the recovery key, mount the subvolumes and restore a
sample from the backup. Verify this and the chosen TPM policy before
installing/enrolling the wallet bridge. Its physical TPM dummy-secret and
restricted-polkit sandbox tests passed, but actual wallet and graphical
authentication with the final integration remain unverified.
