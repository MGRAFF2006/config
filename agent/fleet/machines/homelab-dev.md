# Hetzner development VM

## Worktree storage and T3 recovery — 2026-11-03

The 172 GiB SSD root disk filled, and `t3code.service` failed. Removing the
rebuildable npm download cache allowed T3 to start; local HTTP and the laptop's
Tailscale HTTPS endpoint returned 200, and the managed Connect relay registered.

VM 110 now has an additional 512 GiB disk on the healthy `bulk` HDD mirror,
serial `homelab-dev-worktrees`, ext4 label `dev-worktrees`. It mounts at
`/srv/development`; the worktrees bind-mount at `~/.t3/worktrees` so existing
paths remain valid. The database, runtime and ordinary `~/Projects` checkouts
remain on SSD. HDD builds may be slower. The disk has `backup=1` and is covered
by the existing nightly VM backup job; today's pre-migration backup completed
at 02:53 Europe/Berlin.

Mount definitions, the T3 missing-mount guard and recovery instructions live in
[the storage setup](../../../systemd/homelab-dev/README.md). Reinstall on this
host with `bash scripts/install-homelab-dev-storage.sh` after mounting the disk
and preparing the verified worktree copy. This installer does not migrate or
delete data.

## Git-only config — verified 2026-10-25

The receive-only config Syncthing registration was removed after Mathis moved
software and the agent kit to Git-only. Files and independent dirty work remain
local. The existing default `~/Sync` registration is preserved. Repeat scope
setup with `scripts/configure-personal-sync.py`; see
[scope and recovery](../../../docs/personal-sync.md). Fetch and integrate
reviewed config commits explicitly; there is no live config-sync propagation.

- Verified 2026-10-02 via SSH, systemd, Tailscale, and installed CLI checks.
- Tailscale name / SSH alias: `homelab-dev`, IPv4 `100.108.73.48`.
- Debian 13 VM 110 on `homelab-pve`, login user `humunkulud`, no desktop.
- 4 vCPU backed by Xeon E5-1650 v3, 32 GiB RAM, 172 GiB SSD root plus
  512 GiB HDD worktree storage; no GPU.
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
