---
name: machines
description: >-
  Choose or operate Mathis's computers using verified machine context. Use for
  remote work, desktop/laptop placement, Syncthing, AI readiness, or config sync.
---

# Machines

Read `agent/fleet/README.md` and the relevant `agent/fleet/machines/<name>.md`
in the config checkout. If locating the checkout from this installed skill,
resolve the skill's symlink to its source under `agent/skills/`.

| Host | Role | Main constraint |
|------|------|-----------------|
| `desktop` | RX 7600 and unattended work | Verify online state; about 15 GiB RAM |
| `laptop` | Interactive work and travel | Can suspend; about 30 GiB RAM |

## Reachability

```bash
tailscale status
ssh -o BatchMode=yes -o ConnectTimeout=5 desktop 'uname -s'
```

The current device is `Self.HostName` in `tailscale status --json`. Do not infer
identity from `/etc/hostname`. Probe only the host needed for the task. If it is
unavailable, continue suitable local work and report remaining remote steps.

## Syncthing shares (both devices when connected)

| Path | Purpose |
|------|---------|
| `~/Documents/config/` | Dotfiles + **agent kit** (this skill's source) |
| `~/Projects/` | Code |
| `~/Documents/` | Docs (nested `config/` ignored via `.stignore`) |

## Agent kit install

Canonical: `~/Documents/config/agent/`

```bash
bash ~/Documents/config/scripts/install-agent-kit.sh
bash ~/Documents/config/scripts/install-agent-kit.sh --check
```

Links the entire `agent/skills` directory into `~/.agents/skills`, shared by
Codex, Cursor, and OpenCode, with individual compatibility links for Claude.
All tools share `agent/GLOBAL.md`. The full dotfile installer is separate.

## Rules of thumb

- Prefer editing files under `Documents/config` or `Projects` over machine-local
  copies of the same content.
- Never assume laptop CPU/GPU/display is available for builds or UI checks.
- Machine-specific packages live in `Documents/config/packages/*-{desktop,laptop}.txt`.
- Put long remote jobs in tmux on the target host. Local tmux does not prevent
  laptop suspension. Report the session and completion/failure.
- Update machine records from verified facts, and keep credentials machine-local.
