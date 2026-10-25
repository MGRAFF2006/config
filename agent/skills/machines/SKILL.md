---
name: machines
description: "Use when choosing or operating Mathis's computers, doing remote work, or managing Syncthing and agent-kit installation."
---

# Work on the verified host

Read the [fleet index](../../fleet/README.md) and the relevant machine record
for current roles, constraints, SSH aliases and sync directions. Resolve this
skill's symlink before following relative paths. Machine facts belong in those
records rather than another table here.

Verify the current device with `Self.HostName` from `tailscale status --json`
and probe the required target's reachability. Follow the
[environment workflow](../../workflows/environment.md) for placement, owned
processes, GUI isolation and handoff to another computer. A bounded direct SSH
operation remains appropriate when simpler than a handoff.

Before syncing, check the actual share, direction and exclusions; independent
project checkouts may contain different dirty work. Keep credentials and runtime
state machine-local. Do not infer that a path is shared on every computer.

Install shared instructions through `scripts/install-agent-kit.sh` in the config
checkout, then run it with `--check`. New Claude per-skill links need an installer
run; verify discovery in the intended runtime. Update the machine record after
a verified capability or configuration change.
