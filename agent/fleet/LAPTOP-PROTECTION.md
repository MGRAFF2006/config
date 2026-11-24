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
   do not replace the off-device backup.
2. Verify the backup and restore representative data, including dirty project
   work and account configuration, without exposing credentials in logs/Git.
   Ensure the backup password is recoverable without this laptop.
3. Prove the complete restore fits before anything is erased. A representative
   restore is not enough. For each of the six subvolumes, including both nested
   ones, record its logical size with `btrfs filesystem du -s` and its
   compression ratio with `compsize`. Then estimate the size the chosen restore
   method writes. `btrfs send` without clone sources (`-c`) or a parent (`-p`)
   and file-level copies such as `rsync` duplicate reflinked and
   snapshot-shared extents. They also store data uncompressed unless the target
   mounts with the same `compress=` option. Compare the total with the final
   LUKS mapping's size: the partition minus the LUKS2 header, 16 MiB by
   default. Keep at least 10% of the mapping free. Preferably restore all six
   subvolumes once into a scratch target of the same size on the homelab,
   such as a sparse zvol or file-backed image, and confirm each one is
   complete. Otherwise, reduce or exclude data deliberately before erasing.
4. Prepare a recovery path that does not depend on this laptop's ESP or boot
   manager. A recovery UKI on the same ESP is a convenience, not the
   independent path. Prove one of these works on this laptop before Secure
   Boot is enforced, and again after it is enforced:
   - Off-disk rescue media that the final Secure Boot policy accepts. Examples
     are shim-signed media when Microsoft's UEFI CA stays in `db`, or media
     whose EFI binaries are signed with the new owner key. The plain Arch ISO
     is unsigned, so it does not qualify.
   - A tested firmware rollback. Mathis, at the laptop, enters firmware setup
     with a known supervisor password, disables Secure Boot, boots the
     unsigned rescue media, and re-enables Secure Boot afterward.
   With either path, demonstrate that it can open the LUKS container with the
   manual passphrase or recovery key, mount the subvolumes, and reach the
   backup over the network. Mathis currently has neither a recovery USB nor an
   external backup disk available. Homelab storage can replace the disk, but
   recovery boot remains an unresolved prerequisite.
5. Arrange an AC-powered maintenance window and explicit reboot authorization,
   with Mathis present for firmware menus. Export current firmware trust data
   and preserve off-device LUKS/header/signing-key recovery material.

## Migration sequence and boundaries

After the verified backup, restore-fit check and recovery boot, prefer creating
a fresh LUKS2 container and restoring the existing Btrfs installation into it.
That erases the current partition contents and therefore requires review of the
exact disk, restore evidence and explicit authorization before execution. No
such erase, partition, boot-order, firmware-key or reboot operation has been
performed.

`luksFormat` only writes a header and keyslots. It does not overwrite the data
area. A restore that never writes some sectors leaves the old plaintext in
them, readable from the raw device. Sanitize the old plaintext before
restoring, from the recovery path, within the same authorized erase:

1. Prefer the drive's NVMe sanitize: crypto erase, or block erase if crypto
   erase is not supported. Check support first in `nvme id-ctrl`
   (`sanicap`). Sanitize is device-wide and reaches blocks that host
   overwrites cannot, such as spare or remapped flash. It also erases the ESP
   and the partition table, so recreate both and restore the ESP from the
   backup. If sanitize is not supported, use an NVMe format with a secure-erase
   setting (`nvme format --ses`). Check `fna` in `nvme id-ctrl` to see whether
   that format covers the whole device.
2. If neither method is supported, overwrite all of partition 2 through a
   throwaway random-key mapping before `luksFormat`. The
   [cryptsetup FAQ](https://gitlab.com/cryptsetup/cryptsetup/-/wikis/FrequentlyAskedQuestions)
   describes this. Record the residual risk: old plaintext can survive in
   spare or remapped flash that host writes never reach.
3. Verify the result before restoring. `nvme sanitize-log` should report
   success. Sampled raw reads at several offsets, including some within the old
   data range, should show no recognizable former content.

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
rebooting, verify every `.efi` file on the ESP. Check them against the
enrolled `db` certificate with `sbctl verify` or `sbverify --cert`. Remove any
leftover unsigned loaders, or make sure no boot entry points to one.

Verify encrypted-root boot, Secure Boot enforcement, the independent recovery
path under the final policy, manual LUKS unlock, and the chosen TPM policy before installing/enrolling the wallet bridge. Its physical
TPM dummy-secret and restricted-polkit sandbox tests passed, but actual wallet
and graphical authentication with the final integration remain unverified.
