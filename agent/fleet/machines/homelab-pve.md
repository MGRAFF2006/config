# Hetzner Proxmox host

- Verified 2026-10-02 via SSH, Proxmox CLI, Tailscale, and a backup restore.
- Tailscale name / SSH alias: `homelab-pve`, IPv4 `100.84.103.102`.
- Proxmox VE 9.2.21 on Debian 13, kernel 7.0.14-20-pve; root administration.
- Xeon E5-1650 v3, 6 cores / 12 threads, approximately 125 GiB usable RAM.
- Intel 545s 512 GB SSD, worn and explicitly accepted; two 4 TB Seagate HDDs
  in ZFS mirror `bulk`. No compute GPU is assigned to guests.
- Always-on rented server for services, development, and trusted CI; unaffected
  by laptop sleep. Desktop profiles and AI tools are not installed on the host.
- SSH and Proxmox administration are private through Tailscale. Web UI:
  https://homelab-pve.tail03caec.ts.net, `root`, Linux PAM realm. Password is
  machine-local; choose it with `ssh -t homelab-pve passwd`, keep in Bitwarden.
- VM 100 services: 2 vCPU, 16 GiB, 80 GiB SSD plus 1 TiB HDD data disk.
- VM 110 development: 4 vCPU, 32 GiB, 160 GiB SSD; see its separate record.
- VM 120 CI: 4 vCPU with CPU limit 3, 32 GiB, 128 GiB SSD; 36 online
  repository runners, shared compute, trusted workflows only.
- Three private guest bridges with outbound NAT; guest forwarding to private
  management networks is blocked. No public TCP 22 or 8006.
- Nightly snapshots of all three VMs at 02:30 Europe/Berlin onto HDD storage;
  one full development VM restore verified. No offsite backup purchased.
- Infrastructure source: `~/Projects/homelab/proxmox` on the laptop;
  operations docs: `~/Documents/homelab-docs/setup.md`.
- Verify: `ssh homelab-pve 'pveversion; qm list; zpool status bulk; pvesm status'`.
- Remaining: offsite backup decision, project workflow execution, deployment
  of homelab applications. No server credentials or keys are stored here.
- Complete guest, network, storage, and backup map: [topology](../HOMELAB.md).
