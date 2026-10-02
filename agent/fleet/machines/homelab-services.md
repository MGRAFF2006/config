# Hetzner services VM

- Verified 2026-10-02 via SSH, Proxmox CLI, filesystem and service checks.
- Hostname / SSH alias `homelab-services`; not enrolled in Tailscale.
  `ssh homelab-services` uses `homelab-pve` as ProxyJump to `10.77.10.10`.
- Debian 13 VM 100 on `homelab-pve`; login `humunkulud`, SSH key and sudo;
  headless, 2 vCPU, 16 GiB RAM, no assigned GPU.
- 80 GiB SSD root and a 1 TiB disk from the host HDD mirror. Ext4 data mount
  `/srv/homelab` contains `appdata`, `data`, `backups`, `dbdumps`, `secrets`.
- Intended for Docker homelab applications; Docker 26.1.5 and Compose 2.26.1
  verified. Docker and QEMU guest agent are active. Application stack deployment
  remains pending; no AI provider tools or shared agent kit were installed here.
- Persistent infrastructure source is the laptop's `~/Projects/homelab`;
  no Syncthing pairing or config checkout has been installed on this guest.
- Network `10.77.10.0/24`, gateway `10.77.10.1`, bridge `vmbr0`; outbound NAT.
  Guest forwarding to private management networks is blocked. No application
  public endpoint has been configured.
- Starts at host boot before development and CI; unaffected by laptop sleep.
- Covered by the host's nightly VM backup, including the HDD data disk.
  Application-specific database dumps remain pending deployment.
- Authentication is machine-local; secrets belong outside Git, with passwords
  in Bitwarden. No credential values are recorded here.
- Verify: `ssh homelab-services 'docker compose version; df -h /srv/homelab;
  systemctl is-active docker qemu-guest-agent'`.
- Host, other guests, networking, and shared storage: [topology](../HOMELAB.md).
