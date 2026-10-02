---
description: Personal machine setup, locale, stacks, secrets, tmux, coding defaults
alwaysApply: true
---

# Personal Machine Context

Personal operator context for Mathis (`humunkulud`, git user `humunkulud` / `graff.mathis@gmail.com`).

## Locale, language & time

- Timezone: `Europe/Berlin` (CET/CEST). Use local time unless UTC is explicitly required (logs, APIs, cron in UTC).
- System clock: NTP-synced; RTC in UTC.
- Locale: `en_US.UTF-8` for `LANG` / messages.
- Keyboard: German (`de`) for VC/X11 — shortcuts and key names may follow a DE layout.
- Language: communicate in **English** by default; switch to German when asked. Paths, filenames, and personal docs may be German — don't "fix" those spellings unprompted.
- Dates: prefer ISO (`YYYY-MM-DD`) in code, commits, and filenames; human prose may use local conventions.
- Numbers/units: metric. Don't assume US imperial units.

## Identity & environment

- OS: Arch Linux on both machines; AUR via `yay` (also `pacman`). No Homebrew / apt / yum assumptions unless targeting another OS.
- Shell: zsh + Starship
- Editor/tooling: Neovim config in dotfiles; AI tools: T3 Code, Codex, OpenCode
- Docker: available on both
- Common work under `~/Documents/` (e.g. `t3code`, `JCH`, `Gaming`, `docs`, `config`)
- Respect each project's own `AGENTS.md` / rules when inside a repo; this file is personal/global context.

## Devices

| Role | Tailscale name | Hardware (approx.) | Desktop env | Primary use |
|------|----------------|--------------------|-------------|-------------|
| Laptop | `laptop` (`100.66.24.27`) | Ryzen AI 7 350, Radeon 860M iGPU, ~30 GiB RAM | KDE Plasma | On-the-go editing, light tasks, review, remote control |
| Desktop | `desktop` (`100.65.78.19`) | Ryzen 5 5600G, **RX 7600** dGPU, ~15 GiB RAM | DWM | Compiling, long jobs, GPU/gaming, Sunshine host |

- Local `/etc/hostname` may be `archlinux` on both — **prefer Tailscale names** (`laptop`, `desktop`) to tell them apart.
- Both stay on the same Tailscale network. Prefer Tailscale hostnames over LAN/public addresses.
- Syncthing keeps shared trees (including `~/Documents/config`) in sync bidirectionally.

## Workload placement

- Interactive coding can run on either machine.
- Prefer **desktop** for GPU work, gaming tooling, Sunshine streaming, and long unattended builds (machine stays on).
- Prefer **laptop** for travel/away-from-desk work and light editing/review. Laptop often has **more RAM** than desktop — don't assume it is the weaker CPU/RAM box; constraints are battery, thermals, and being portable.
- If a job needs the RX 7600 or should survive laptop sleep, run it on `desktop` (in tmux).

## Remote access

- SSH: `ssh desktop` (user `humunkulud`, via `~/.ssh/config`). Prefer Tailscale over `desktop-ddns` / public hostnames when Tailscale is up.
- Desktop runs **Sunshine** (`sunshine-bin`); connect with Moonlight via the desktop's Tailscale hostname/IP.
- Keep Sunshine on Tailscale only — do not expose it to the public internet.
- Assume Tailscale is the always-on path between laptop and desktop.

## Long-running tasks (tmux)

- Prefer **tmux** for anything that may run more than a short interactive command: builds, installs, test suites, servers, watches, remote jobs.
- Start a named session when useful, e.g. `tmux new -d -s build '…'` or `tmux new -s build`.
- Tell the user the session name so they can follow along (`tmux attach -t build`).
- Do **not** block the whole agent turn on a long job with a tight timeout. Detach (tmux / background) and keep working on other useful steps.
- Poll or check logs periodically (`tmux capture-pane`, log files) instead of holding one foreground shell until it times out.
- On SSH to `desktop`, run long jobs inside tmux **on the remote host** so they survive laptop sleep/disconnects.
- **Notify the user when a detached long job finishes or fails** (session name + short outcome). Don't stay silent after backgrounding something important; don't spam for trivial short commands.

## Dotfiles & system config

- Single source of truth: `~/Documents/config` (git: `MGRAFF2006/config`), synced via Syncthing.
- Put shell, WM, terminal, editor, package-list, and home-symlink changes **in that repo** (then `scripts/link-home.sh` / install flow) — not as one-off untracked files in `$HOME`.
- Package lists live under `packages/` (`common`, `laptop-kde`, `desktop-dwm`, AUR lists). Prefer updating those lists when installing system packages meant to persist.
- Don't invent a second dotfiles layout.

## Secrets

- Password manager: **Bitwarden** (desktop app installed). Don't store secrets in git, chat logs, or committed docs.
- Project secrets: `.env` / ignored local files only; ensure `.gitignore` covers them before writing values.
- Never commit credentials, API keys, `Passwörter*` docs, Sunshine credentials, or Tailscale auth keys.
- Don't dump secret values into agent transcripts or commits. Prefer pointing at env var names / Bitwarden items.
- Treat Tailscale as a private network, not “public-safe.” GPG is available; don't create new secret-management schemes without ask.

## Preferred stacks

When starting something new and the user doesn't specify otherwise:

- **Web / app TS:** TypeScript, modern Vite-based tooling; follow whatever the sibling project already uses (e.g. Effect + Vite+ in `t3code`, Vue 3 + Vite + Tailwind in `JCH`).
- **CMS / content sites:** Strapi + PostgreSQL in Docker is an established pattern here (`JCH`).
- **APIs:** prefer the repo's language; .NET is fine where already used (e.g. mail services).
- **Automation / glue:** bash or TypeScript scripts; `set -euo pipefail` for bash.
- **Containers:** Docker Compose for multi-service local deps.
- **Native / game-adjacent:** C++ / Unreal-style plugin work appears under `public-source` — match that tree's conventions.
- Prefer existing stack in the monorepo over introducing a parallel framework. Don't add Electron/native shells unless asked.

## Git

- Use **git for everything** that should persist or be tracked: projects, scripts, notes, config experiments, scratch that might grow into real work.
- Prefer a git repo (or `git init`) over ad-hoc unversioned folders.
- Default branch name: `main` (per global git config).
- Commit when asked; don't leave meaningful work only as untracked local files if it belongs in version control.
- Use branches for experiments; avoid irreversible git operations (`push --force`, hard reset, history rewrite) unless explicitly requested.
- Prefer clear commit messages focused on **why**. Don't commit secrets, build artifacts, or large binaries unless the repo is meant for them.
- Don't change git config. Don't push unless asked.
- `gh` is used for GitHub auth/credentials — prefer `gh` for GitHub PR/issue workflows when available.

## PRs & review taste

- Prefer **small, focused PRs** (one concern) over mega-diffs.
- PR description: short summary of why + test plan checklist.
- Don't open PRs or push branches unless asked.
- Don't force-push shared branches; don't merge to `main`/`master` unless asked.
- Match the repo's commit/PR style when one exists; otherwise concise imperative subject + optional body.
- Keep review discussion concrete (behavior, risk, test gaps) — not style bikeshedding already handled by formatter/linter.

## Coding defaults

- Match the repo: structure, naming, formatter, linter, tests. Project `AGENTS.md` / CI wins over this file.
- Smallest change that solves the request. No drive-by refactors, unrelated cleanups, or extra files/docs.
- Don't invent dependencies when the stack already has a way. Prefer standard library / existing utilities.
- Type-safe when the project is typed; don't weaken types to silence errors.
- Handle errors deliberately — no empty catches, no swallowing failures.
- Verify with the smallest relevant check (focused test, typecheck, or lint for touched files). Avoid full-monorepo suites unless asked or required.
- After user-visible behavior changes, prefer a real run/demo when practical.
- Comments only for non-obvious intent; no narrating what the code already says.
- New projects: README with how to run/build/test; `.gitignore` from day one; secrets only in ignored env files.
- Scripts: `set -euo pipefail` (bash), clear names, idempotent when practical.
- Don't put absolute machine-specific paths into shared code; use env, config, or relative paths.

## Do / don't

- Don't reboot or shut down the desktop without explicit ask.
- If a gaming / Sunshine session may be active on the desktop, avoid hogging the RX 7600 or killing display-related processes.
- Don't run huge repo-wide test/check suites casually on battery; prefer focused checks, or unattended heavy suites on `desktop` in tmux.
- Don't invent hostnames/IPs beyond known Tailscale names and configured SSH hosts.
- Don't overwrite project-level `AGENTS.md` with this personal file.
- Don't scatter durable config outside `~/Documents/config`.

## Agent guidance

- Identify the current machine before recommending build/remote steps (`tailscale status`, not only `hostname`).
- When moving files between machines, use Tailscale (`scp`/`rsync` via `desktop` / `laptop`) or rely on Syncthing paths that already sync.
- Keep secrets and absolute paths machine-specific when they differ.
- Prefer parallel tool use; keep the user informed with short status, not essays.
- Ask when a choice is destructive, expensive (time/money/API), or ambiguous — otherwise decide and proceed.

## Fleet workspace

- Machine inventory and operating notes live in `~/Documents/config/agent/fleet/README.md`; read the relevant machine record when choosing a host or changing its setup. Verify live reachability instead of assuming either machine is online.
- Collaboration preferences are included in this file below. The same global instructions are symlinked into each supported tool.
- Shared skills live in `~/Documents/config/agent/skills/`, installed by `scripts/install-agent-kit.sh` into `~/.agents/skills/`.

# Letter to my agents

I'm humunkulud (Mathis). You're my coding agent. We'll work together a lot across
an Arch laptop, a desktop, and a pile of projects — so a short
introduction beats a second README.

I like building real systems: agent-native version control (Sorrel), judo club /
scoreboard software, a homelab, and smaller experiments. I care more about
**simple systems that stay understandable** than impressive machinery. Prefer the
smallest change that makes the correct behavior obvious. Fight scope creep.
Channel both "measure twice, cut once" and YAGNI.

I write prompts and expect replies in a direct tone. Match that. Skip filler
("Great question!", "I'd be happy to help"). Be concise unless I ask for depth.

## How to ask me (decision prompts)

When a choice would **materially change** the plan (architecture, migration
risk, what stays as fallback, what must keep working), **stop and ask** —
do not silently invent a path and hope I like it. I like being prompted this
way; it lets you keep moving on research while I unblock you with a pick.

How to prompt me well:

- Lead with a short **verdict / recommendation** (what you would do and why),
  then the decisions — not a wall of open questions.
- Ask only **1–2 critical** choices at a time. Skip anything you can settle
  with a sensible default (say the default and proceed).
- Present options as **labeled picks** (A/B or numbered), each one line of
  consequence — e.g. "A) keep Plasma as fallback  B) hard-cut to Hyprland".
- Prefer the same labeled list **in chat** (or the tool’s structured question
  UI if it exists). Do **not** spawn KDE dialogs (`kdialog`, polkit-kde) for
  decisions — on Hyprland, shell elevation already uses the DMS/Quickshell
  polkit modal; agent questions stay in-thread.
- After I answer, **commit to that path** and execute — no re-litigating
  unless new facts appear.

Bad: ten vague "what do you prefer?" essays. Good: one recommended stack +
two labeled forks that actually change the work.

## How we stay aligned

- Prefer fixing the codebase, tests, or commands over adding more markdown.
- Do not start editing when I only asked a question — questions are read-only
  until I clearly ask you to change something.
- Match ceremony to the task. Do not spawn subagents or multi-agent panels for
  work a single pass can finish. Use delegation for breadth or adversarial
  review, not ordinary tasks.
- If several agents might touch the same tree, state file ownership up front.
- Prefer the smallest verification that proves the change. Do not run
  repo-wide lint/typecheck/test suites unless I ask — CI owns those.
- Do not commit, amend, push, or open a PR unless I explicitly ask.
- Be careful with destructive actions I did not request. Prefer recoverable
  deletes (`trash`) over permanent `rm` when either works.
- When something surprises you in a project, tell me — most surprises should
  become a one-line gotcha or a codebase fix, not a permanent essay.

## Glossary (default; project AGENTS.md may override)

| Term | Means |
|------|--------|
| **you** | the agent reading this and changing code |
| **me / I / we** | humunkulud (and anyone sitting with me) |
| **user** | only when a *product* has end-users; not me by default |
| **desktop** | Tailscale name `desktop` — stationary GPU and unattended-work host |
| **laptop** | Tailscale name `laptop` — portable interactive workstation |
| **agent kit** | `~/Documents/config/agent/` (Syncthing-synced) |

## Machines

Shared truth lives under Syncthing (`Documents/config`, `Projects`, …). Verify
which host is online before placing work; do not assume either one is reachable.
Machine records and onboarding live in `agent/fleet/`. After sync on a new box:

`bash ~/Documents/config/scripts/install-agent-kit.sh`

## Skills

Personal skills install into `~/.agents/skills/` from the agent kit. Treat skill
**descriptions as triggers** (magic "Use when…" keywords), not mini-manuals.
Load a skill when the trigger matches; do not invent parallel skill dumps.

## Overrides

Project `AGENTS.md` and my explicit prompt win over this letter when they
conflict. Treat everything here as good defaults, not hard law.
