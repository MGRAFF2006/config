# Windows desktop on homelab-dev

Browser console: <https://homelab-dev.tail03caec.ts.net/windows/>.
Connect Tailscale first. This is the full graphical Windows desktop, controlled
with a browser keyboard and mouse. The host needs no physical monitor.
T3 continues to use the root URL. The console is authenticated by the existing
private tailnet access rules; it opens an automatically signed-in Windows session.

Windows 11 Pro is downloaded directly from Microsoft by Dockur Windows 6.06.
The container image is pinned by digest. Office LTSC Professional Plus 2024,
x64, uses an English interface and German proofing tools. The first-logon OEM
script installs Office using Microsoft's signed Office Deployment Tool.
The local Windows account is `Mathis`; its generated password is saved in
Bitwarden under **Homelab Windows VM**. Runtime `.env` stays only on the host
with mode 0600 and is excluded from Git.

The VM uses nested KVM, two CPU cores and a 96 GiB growable disk on
`/srv/development/windows-vm`, outside the development host's SSD root.
Configured RAM is 6 GiB, automatically reduced by Dockur when the host needs
more memory. The container is limited to two CPU cores and 8 GiB RAM.
There is no GPU acceleration. Audio and shared host folders are disabled.
Only the web console is published, on loopback port 8006; RDP and VNC ports
are not published. Tailscale Serve supplies HTTPS on `/windows/`.

The QEMU Guest Agent is installed from Fedora's pinned, signed MSI. Its channel
uses only a Unix socket inside the container, not a network port. The OEM script
restores UAC, normal Windows updates and secure SMB client defaults that the
upstream unattended installation changes. Restart after provisioning so UAC
takes effect.

As explicitly requested for this VM, activation uses third-party
[Microsoft Activation Scripts](https://github.com/massgravel/Microsoft-Activation-Scripts),
version 3.12, commit `6401d2f36975dc07bcb6d22ea823a8498a75ec01`.
The script is downloaded with a pinned SHA-256, rather than executed from a
changing remote command. Windows uses HWID with edition changes disabled;
Office uses TSforge StaticCID without an Ohook DLL or renewal task. This is
not a Microsoft-issued product license. Major feature upgrades may require
reactivation. Provisioning checks actual licensing status and saves the local
result in `C:\VMSetup\status.json`; its log stays at `C:\VMSetup\setup.log`.

Run on `homelab-dev` from this directory:

```bash
bash setup.sh                 # initial setup / restore configuration
docker compose logs --tail 50 # startup and installation status
docker compose stop          # graceful shutdown; preserve Windows files
docker compose start         # resume
```

Docker starts the VM again after a host restart unless it was explicitly stopped.
The development data disk is included in Proxmox VM 110's existing backups;
those snapshots do not quiesce the nested Windows filesystem.

To remove just the browser route while preserving T3 and Windows storage:

```bash
sudo tailscale serve --bg --yes --set-path=/windows off
```

Do not reset all Tailscale Serve routes: that would also remove T3's route.
Keep the Windows disk and `.env` when moving or updating this configuration.

The initial Enterprise Evaluation disk was preserved at
`/srv/development/windows-vm-evaluation-2026-11-04` before installing Pro.
Evaluation cannot be permanently activated; the active VM uses the separate
regular Pro installation.
