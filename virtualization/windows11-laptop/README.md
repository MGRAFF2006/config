# Windows 11 on the laptop

Local libvirt VM `windows11`, managed by **Virtual Machine Manager** under
**QEMU/KVM** (`qemu:///system`). Open the VM and select its console; press the
play button when it is stopped. Direct console command:

```bash
virt-manager --connect qemu:///system --show-domain-console windows11
```

## Configuration

- KVM, Q35, host CPU passthrough, one socket with four cores and 8 GiB RAM.
- 80 GiB growable QCOW2 disk: `/var/lib/libvirt/images/windows11.qcow2`.
- OVMF UEFI with Secure Boot support and an emulated TPM 2.0. The distribution's
  firmware template has no enrolled signing keys, so Secure Boot enforcement
  is not enabled. No Windows hardware checks were bypassed.
- SATA storage and Intel e1000e networking use Windows' built-in drivers.
- `passt` provides outbound networking without a bridge, DHCP service, firewall
  exceptions or published inbound ports.
- SPICE console through libvirt, QXL display, USB tablet and ICH9 sound.
- VM autostart is disabled; starting the laptop does not consume VM memory.
- English interface, German keyboard and regional formats, Berlin time zone.
- Local administrator account `Mathis`, with its password supplied privately.
  Persistent automatic sign-in is enabled at Mathis's request. Its credential
  state stays inside Windows.

The existing `Win11_25H2_EnglishInternational_x64_v2.iso` was reused. Its observed
SHA-256 is `66b7b4b71763ed6f9b2ce29326ed9284544da6f5283d00329921540c01aaaeea`;
this records the local media, not a comparison with a publisher checksum.
The libvirt copy in `/var/lib/libvirt/boot/windows11-25h2.iso` uses a Btrfs reflink
to avoid duplicating the ISO's data. Installation selects Windows 11 Pro.
The installation's product-key page was skipped without a key. Account settings
were added only to a private, temporary answer disc under `/run/`, separate from
this repository. That disc, its host files, the private input file and cached
guest answer files were removed after installation. Never commit an answer file
containing passwords.

## Verified 2026-11-04

Windows 11 Pro 25H2, build 26200.8037, completed a clean shutdown and cold start
with both installation discs ejected. It automatically signed in as
`MATHIS-WIN11\Mathis`. Windows reported all four cores, a ready TPM 2.0, the
German keyboard layout and the Berlin time zone. A separate Windows logon check
validated the supplied password. HTTPS to Microsoft returned 200.

The official Fedora `virtio-win-guest-tools.exe` bundle 0.1.302 completed with
exit code 0. QEMU Guest Agent and Spice Agent are running, and the Red Hat QXL
display driver is active. Its console rendered in Virtual Machine Manager in
the isolated agent desktop. The final guest resolution was 1024 × 768; interactive
resize testing ended when Mathis's own console connected. Sound playback was
not tested. About 46.1 GiB was free inside Windows after Office installation.

Installer: [Fedora virtio-win 0.1.302](https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-0.1.302-1/).
Observed installer SHA-256:
`d8ae9ea1e943384ac195e012cd36f82c3161620e5fc9529be4e42e6f420e222d`.

## Office and activation — verified 2026-11-04

Office LTSC Professional Plus 2024 x64, version `16.0.17932.21056`, was installed
from Microsoft's CDN using [office-2024.xml](office-2024.xml). Office Deployment
Tool `16.0.20430.20146` and its extracted installer had valid Microsoft
signatures. Word, Excel, PowerPoint, Outlook, OneNote and Access are installed;
all six executable signatures were valid. English (UK) and German resources
are present. Updates use the `PerpetualVL2024` channel.

At Mathis's request, activation used third-party
[Microsoft Activation Scripts 3.12](https://github.com/massgravel/Microsoft-Activation-Scripts/tree/6401d2f36975dc07bcb6d22ea823a8498a75ec01),
pinned at `6401d2f36975dc07bcb6d22ea823a8498a75ec01`. A separate agent reviewed
the selected paths before execution, and the transferred files' SHA-256 values
matched that revision. The selected invocations were:

```cmd
HWID_Activation.cmd /HWID /HWID-NoEditionChange
TSforge_Activation.cmd /Z-Office /Z-SCID
```

The Windows edition remained Pro. TSforge's Office-only StaticCID method was
used; Ohook was not installed. Both Windows and the installed Office product
reported `LicenseStatus=1` with no grace period after both operations. Office's
own `OSPP.VBS` reported the active ProPlus 2024 MAK product as `LICENSED`, and
`slmgr.vbs /xpr` reported permanent Windows activation. Unused Office licensing
templates remained unlicensed, as expected. Automatic Mathis sign-in remained
enabled. Interactive Office first-run dialogs were not exercised while Mathis's
console was in use.

Before activation, a root-only rollback checkpoint was saved at
`/var/lib/libvirt/images/windows11-checkpoints/2026-11-04-before-activation/`.
It contains the disk, saved RAM, NVRAM, TPM state and domain definition. Disk
metadata passed `qemu-img check`, and libvirt parsed the saved-memory image's
definition. The VM resumed successfully afterward; a separate rollback was not
performed. Preserve current VM state before deliberately restoring this older
checkpoint. Checkpoint files and activation logs stay machine-local, outside Git.

## Host setup and recovery

The existing config setup flow's virtualization service actions were applied:
`libvirtd.service` is enabled, and `humunkulud` belongs to `libvirt`. The packaged
polkit rule permits that group to manage system VMs. The existing virtualization
package selection already includes the required tools.

```bash
python3 scripts/setup.py --profile laptop --components virtualization \
  --no-links --services --plan
```

Review the plan before applying it with `--apply --yes`. Package installation
is separately selected by the setup tool and was unnecessary on this host.

Use Windows' own Shut down command or libvirt's graceful shutdown:

```bash
virsh --connect qemu:///system shutdown windows11
virsh --connect qemu:///system start windows11
```

Keep the QCOW2 disk, the VM's NVRAM and `/var/lib/libvirt/swtpm/` state together
when making a complete backup or migrating the VM. Export its current definition
with `virsh --connect qemu:///system dumpxml --inactive windows11`. Back up with
the VM shut down. No VM backup job was added.

The host had 107 GiB free before installation and about 71 GiB after Office and
the rollback checkpoint. The checkpoint uses reflinks but retains old blocks
when the VM changes. Monitor host space as Windows grows; keep at least 10 GiB
free.

## Installation answer file

`Autounattend.xml` is a record of this VM's installation settings. It erases
**guest disk 0** and installs Windows there. Use it only with a new isolated
virtual disk; never attach host disks to a VM using this answer file. It has no
account passwords, activation key or authentication state. It automates disk
layout and Windows installation, and stops at personal first-run setup unless
a private account configuration is added at runtime.

Keep the answer disc attached until Windows has finished installation. On the
first attempt, replacing it with a tools disc during image application caused
Windows Setup to fail with `0x80070002` when copying `E:\autounattend.xml` into
the installed system. Installation media and tools must remain available on the
same disc, or the tools must be attached separately after setup completes.

Sources: [Windows installation media](https://www.microsoft.com/en-us/software-download/windows11),
[unattended setup](https://learn.microsoft.com/windows-hardware/manufacture/desktop/automate-windows-setup?view=windows-11),
[libvirt Secure Boot](https://www.libvirt.org/kbase/secureboot.html),
[Office LTSC 2024 deployment](https://learn.microsoft.com/en-us/office/ltsc/2024/deploy).
