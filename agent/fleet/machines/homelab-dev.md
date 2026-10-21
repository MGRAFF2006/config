# Hetzner development VM

- Verified 2026-10-02 via SSH, systemd, Tailscale, and installed CLI checks.
- Tailscale name / SSH alias: `homelab-dev`, IPv4 `100.108.73.48`.
- Debian 13 VM 110 on `homelab-pve`, login user `humunkulud`, no desktop.
- 4 vCPU backed by Xeon E5-1650 v3, 32 GiB RAM, 160 GiB SSD root; no GPU.
- Intended for remote development and unattended AI work. Host stays on;
  laptop sleep and SSH logout do not stop the background service.
- Config checkout: `~/Documents/config`, cloned from MGRAFF2006/config;
  the current shared agent kit and installer were copied from the laptop.
  Focused dry-run/install/check completed. No full desktop dotfile profile.
- Syncthing installed but not paired or running; synchronization is pending.
- T3 Code 0.0.44 and Codex CLI 0.160.0 installed by their standalone installers
  at `~/.local/bin`. Git, SSH, rsync, tmux, ripgrep, Docker, Compose v2,
  Node.js/npm, and build tools are installed.
- T3 `t3code.service` active and enabled, systemd user lingering enabled;
  service PATH includes `~/.local/bin` so it can locate Codex.
- Tailscale Serve maps HTTPS to loopback T3 server at port 3773:
  https://homelab-dev.tail03caec.ts.net. Operator permission belongs to
  `humunkulud`. Client pairing/login remains machine-local.
- In T3 Code, add an SSH environment `homelab-dev`, or generate a fresh
  pairing link with `~/.local/bin/t3 pair --tailscale` on this VM.
- Provider credentials were not copied. Normal browser OAuth with an SSH
  callback tunnel completed Codex sign-in; `codex login status` confirms
  Logged in using ChatGPT. Device-code login is disabled in this account.
- Verify: `ssh homelab-dev 'export PATH="$HOME/.local/bin:$PATH"; t3 --version;
  codex --version; systemctl --user is-active t3code.service;
  loginctl show-user humunkulud -p Linger'`.
- Read project-specific instructions and use remote tmux for builds. Do not
  assume the global laptop/desktop Arch package commands apply to Debian.
- Host, other guests, networking, and shared storage: [topology](../HOMELAB.md).
