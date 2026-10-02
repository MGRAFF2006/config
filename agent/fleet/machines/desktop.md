# Desktop

Stationary workstation. User-reported baseline: Arch Linux, Ryzen 5 5600G,
RX 7600 discrete GPU, about 15 GiB RAM, DWM. Tailscale identity: `desktop`
(`100.65.78.19`); connect with the existing `ssh desktop` configuration.

## Verification status

On 2026-10-02 Tailscale reported this device offline. Hardware and desktop
environment above come from Mathis's existing instructions; packages, provider
logins, shell PATH, available disk space, and agent-kit installation have not
been inspected remotely. Verify them when it returns. Do not copy laptop tool
versions into this record.

## Workload placement

Prefer this host for work needing the RX 7600 and unattended jobs that should
survive laptop sleep. Check available RAM before assigning a large build.
Ask about an active gaming or Sunshine session before running a substantial
GPU workload; do not kill display processes or reboot without authorization.

Use tmux on this host for long work. Pick a task-specific session name and
give Mathis the attach command and outcome when the job finishes or fails.

## Access and services

- `ssh desktop` uses the established Tailscale path. Verify with
  `tailscale status`, `tailscale ping desktop`, and a bounded SSH probe before
  relying on the connection. Do not fall back to a public address automatically.
- Sunshine (`sunshine-bin`) is the reported Moonlight host. Keep it reachable
  through Tailscale only.
- Shared config and Fleet live in `~/Documents/config`. Confirm Syncthing has
  finished syncing before editing the same file from both hosts.
- Install agent context with `bash scripts/install-agent-kit.sh` from the
  config checkout, then run `--check`. Authenticate each provider on this host
  through its normal login flow; do not copy auth files from the laptop.

## When it returns

Verify the device identity, session, hardware, AI executable paths/versions,
Syncthing service, SSH, and kit links. Update this record with the date and
observed facts. If it remains unavailable, continue laptop-safe work and report
which requested remote steps remain unfinished.
