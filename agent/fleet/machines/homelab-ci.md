# Hetzner CI VM

- Verified 2026-10-02 via SSH, Proxmox CLI, Docker, and runner service checks.
- Hostname / SSH alias `homelab-ci`; not enrolled in Tailscale.
  `ssh homelab-ci` uses `homelab-pve` as ProxyJump to `10.77.30.10`.
- Debian 13 VM 120 on `homelab-pve`; administration user `humunkulud`, SSH key
  and sudo; headless, 4 vCPU with host CPU limit 3 and CPU units 512,
  32 GiB RAM, 128 GiB SSD root, no assigned GPU.
- Intended for trusted GitHub Actions jobs. At verification, 36 repository
  runner services were running, named `homelab-<repository>` and labeled
  `self-hosted`, `Linux`, `X64`, `homelab`. Each repository has `CI_RUNNER=homelab`.
- Runner version at setup 2.337.0, automatic updates enabled; services
  `actions.runner.*` run as `github-runner`, with state and work directories
  under `/var/lib/github-runner/<repository>`.
- Docker 26.1.5 and Compose 2.26.1 verified; a real Docker container test passed.
  Docker and QEMU guest agent are active. No personal provider credentials or
  shared agent kit have been installed on this VM.
- All repository runners share the VM and its resource limits; they are not
  isolated from each other. One job per repository runner, no global queue.
  Use GitHub-hosted runners for external/untrusted PRs. macOS, Windows, and
  GPU jobs require appropriate runners outside this Linux CPU VM.
- Infrastructure source: laptop `~/Projects/homelab/proxmox`; job checkouts
  are managed by Actions. No Syncthing pairing or personal config checkout.
- Network `10.77.30.0/24`, gateway `10.77.30.1`, bridge `vmbr2`; outbound NAT,
  with forwarded access to private networks and the tailnet blocked.
- Starts at host boot after services and development; unaffected by laptop
  sleep. Included in nightly VM snapshots to the host HDD mirror.
- Runner credentials remain local to their registration directories, outside
  Git. No credential values or development login caches are recorded/copied here.
- Verify: `ssh homelab-ci 'docker compose version; systemctl list-units
  --type=service --state=running "actions.runner.*"; df -h /'`.
- Host, other guests, networking, and shared storage: [topology](../HOMELAB.md).
