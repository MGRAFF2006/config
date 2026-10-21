---
name: onboard-machine
description: Set up or verify a computer for Mathis's AI fleet when adding, replacing, or preparing a development machine. Use the existing config repo and record verified capabilities.
---

# Onboard a machine

Find the config checkout, then read `agent/fleet/ONBOARDING.md` and the target
machine record if one exists. Use Tailscale identity and current reachability;
do not assume this is the laptop or that the desktop is online.

Inspect existing tools and links before installing anything. Use
`scripts/install-agent-kit.sh --dry-run`, then install the authorized kit and
run `--check`. The full `link-home.sh` also affects desktop and shell settings;
use it only when those changes belong to the request.

Use the onboarding guide's host-specific checks and normal provider login
flows. Never transfer auth files or private keys through the shared repo.
Use `machines/TEMPLATE.md` for a new record, update the Fleet index, and label
unverified facts. Report completed steps and any offline-host or login blockers.
Do not install a local model runtime or change power settings unless requested.
