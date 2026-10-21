# Mathis's AI fleet

Open this folder as a project in T3 Code, OpenCode, or your agent of choice when
you want help with your computers or AI workflow. It gives the agent a maintained
map of your machines and links to repeatable procedures. For application work,
open the application's own repo instead.

This is part of `~/Documents/config`, already shared through Syncthing. There
is no second dotfiles repo, background orchestrator, or new paid service.

## Start here

```bash
cd ~/Documents/config
bash scripts/install-agent-kit.sh --dry-run
bash scripts/install-agent-kit.sh
bash scripts/install-agent-kit.sh --check
```

The installer links shared skills and agent instructions, backing up replaced
files under `~/.local/share/agent-kit-backups/`. It installs no packages, changes
no services, and makes no model calls. Use it on each machine after the repo
arrives there. Instructions and existing skills pick up edits through Syncthing.
New skills appear automatically through the shared directory for Codex
and OpenCode; rerun the installer to add their Claude links. Restart sessions
after changing context.

Try this first in a new Fleet thread:

> Check which computer you are on and what is available. Read its Fleet record,
> compare it with the live state, and report any important drift. Do not install
> or change anything yet.

Then try an actual task:

> I want to work on JCH from this laptop. Find the checkout, read its own
> instructions, and get the existing development setup running. Explain how I
> can verify it works and how to stop the processes you start.

## Computers

| Machine | Use it for | Record |
| --- | --- | --- |
| `laptop` | Interactive work, travel, light checks, research | [Laptop](machines/laptop.md) |
| `desktop` | RX 7600 work and jobs that must survive laptop sleep | [Desktop](machines/desktop.md) |
| `homelab-pve` | Hetzner hypervisor, VM/storage administration | [Proxmox host](machines/homelab-pve.md) |
| `homelab-dev` | Remote T3 Code, development and unattended CPU work | [Development VM](machines/homelab-dev.md) |
| `homelab-services` | Docker homelab applications and bulk data | [Services VM](machines/homelab-services.md) |
| `homelab-ci` | Trusted GitHub Actions jobs across project repositories | [CI VM](machines/homelab-ci.md) |

The Hetzner host and its three VMs are mapped in the
[homelab topology](HOMELAB.md), including private networks, storage, backups,
and access paths. Prefer `homelab-dev` for unattended CPU development work;
use `desktop` when a job needs the RX 7600. Reserve `homelab-ci` for CI jobs.
Verify the selected host is reachable before starting work.

Confirm identity with `tailscale status` or `tailscale status --json`; the JSON
`Self.HostName` identifies the current device. `/etc/hostname` may be `archlinux`
on both. The desktop was offline during initial setup; that is an observation,
not a permanent property. Do not assume the laptop is weaker in RAM.

## What to read

| Need | Document |
| --- | --- |
| Daily AI workflow, prompts, and proof | [Working with AI](WORKFLOW.md) |
| Add or replace a computer | [Onboarding](ONBOARDING.md) |
| Public evidence about Theo and recreations | [Research](RESEARCH.md) |
| Personal defaults and communication preferences | [Shared instructions](../GLOBAL.md) |
| Write useful project instructions | [Project template](../AGENTS.template.md) |

## Which tool reads what

| Tool | Global instructions | Personal skills |
| --- | --- | --- |
| Codex, including when launched by T3 Code | `~/.codex/AGENTS.md` → `GLOBAL.md` | `~/.agents/skills` → entire shared directory |
| OpenCode | `~/.config/opencode/AGENTS.md` → `GLOBAL.md` | Same shared skills |
| Claude Code, if used | `~/.claude/CLAUDE.md` → `GLOBAL.md` | `~/.claude/skills/<name>` → shared skill |

Custom `CODEX_HOME` and `XDG_CONFIG_HOME` are respected. T3 Code is the interface;
the selected harness determines instruction and skill discovery. Local skills
do not automatically appear on a remote host or cloud worker; install there
and verify in that session. Discovery paths are documented by
[OpenAI](https://learn.chatgpt.com/docs/build-skills),
[OpenCode](https://opencode.ai/docs/skills/), and
[Claude Code](https://code.claude.com/docs/en/skills).

`GLOBAL.md` combines your existing personal instructions and collaboration
letter. All tools read that same file. Older `PERSONAL.md` and `LETTER.md`
paths are compatibility symlinks; there is no rendering step or second copy.
See [the shared kit guide](../README.md) for the full link layout.

## Maintain it

Change machine records when hardware, connection methods, or important services
change. Date verified observations; never turn a past online status into a rule.
Save useful research as concise sourced notes, not complete transcripts.
Add a skill only when a repeated task benefits from it; keep the description
specific so unrelated tasks do not activate it. Keep credentials and tool state
on each device, outside this repo. Commit these changes when you are ready;
installation itself does not create a commit or push anything.
