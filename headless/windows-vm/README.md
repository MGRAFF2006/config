# Windows desktop on homelab-dev

Browser console: <https://homelab-dev.tail03caec.ts.net/windows/>.
Connect Tailscale first. This is the full graphical Windows desktop, controlled
with a browser keyboard and mouse. The host needs no physical monitor.
T3 continues to use the root URL. The console is authenticated by the existing
private tailnet access rules; it opens an automatically signed-in Windows session.

Windows 11 Enterprise evaluation is downloaded directly from Microsoft by
Dockur Windows 6.06. The image is pinned by digest. The evaluation lasts 90 days;
see [Microsoft's evaluation guidance](https://www.microsoft.com/en-us/evalcenter/evaluate-windows-11-enterprise).
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
