# Arch Linux, in one place

My personal setup for a portable laptop and a stationary desktop: versioned dotfiles, package lists, and scripts to put everything back where it belongs.

**Zsh + Starship · Neovim · Alacritty · Hyprland + DMS / KDE Plasma / DWM**

The configuration lives here; home-directory files are linked into it. Syncthing keeps the repository shared between machines.

Start with [package lists](packages/), [home configuration](home/), or the [Fleet records](agent/fleet/README.md). The [system manifest](docs/system-manifest.md) is a historical snapshot, not the deployment specification.

## Machines

| Hostname | Role | WM | Shell |
|---|---|---|---|
| `desktop` | Desktop (stationary) | DWM (primary); Hyprland+DMS optional later | ZSH + Starship |
| `laptop` | Laptop (portable) | Hyprland+DMS observed 2026-10-02; KDE Plasma available | ZSH + Starship |

Optional Hyprland + Dank Material Shell: see [docs/hyprland-dms.md](docs/hyprland-dms.md).
Install on laptop with `bash scripts/install-hyprland-dms.sh laptop`; preview with `--dry-run`.
The default installs the session alongside the existing login manager.
`--with-greeter` explicitly applies the laptop-specific Howdy/PAM setup.

## Fast config deployment

From an existing checkout, on a machine whose packages are already installed:

```bash
cd ~/Documents/config
bash scripts/link-home.sh laptop --dry-run
bash scripts/link-home.sh laptop
bash scripts/link-home.sh laptop --check
```

Use `desktop` for the other workstation. With no machine argument the linker
uses `MACHINE_TYPE` or the live Tailscale identity (including `homelab-dev`); it never guesses from the
local hostname. It accepts `CONFIG_LINK_HOME` for an isolated destination.
Correct links are left alone. Replaced files, directories, and symlinks go to
`~/.local/share/config-link-backups/<timestamp>-<unique suffix>/`, retaining their
relative paths. To restore one, remove its new link and move that backup back
to the same path. Backups are created only when something is replaced.

This is the quick path: no downloads, upgrades, service activation, MIME-default
changes, or Git pulls. Managed SSH includes are added with a backup while local
keys and custom host entries are retained. A linked SSH config needs its includes
managed in its own source. Run `systemctl --user daemon-reload` after changing unit
files. Enable optional services deliberately; linking a unit does not enable it.
For the existing laptop lid behavior, that command is
`systemctl --user enable laptop-lid-awake.service`.

## Fresh workstation setup

Start with a working Arch installation, networking, a normal user, and sudo.
Disk layout, bootloader installation, encryption, and restoring secrets remain
outside this installer.

```bash
sudo pacman -Syu --needed git
git clone https://github.com/MGRAFF2006/config ~/Documents/config
cd ~/Documents/config
bash scripts/install.sh laptop --dry-run
bash scripts/install.sh laptop
```

Use `desktop` for DWM. The installer performs a full Arch upgrade, installs
common and machine packages, bootstraps yay if needed, installs AUR packages,
links configs, and enables workstation services. A package failure stops the
run; fixing it and rerunning is supported. `--skip-aur` installs only official
packages and links config; AUR applications must then be installed separately.
The installer uses its own checkout without pulling or changing branches.
AUR compilation and application downloads determine fresh-install speed.
Use tmux for these longer runs, for example `tmux new -s config-install`.

Hyprland/DMS remains a separate setup; PAM and greeter changes are opt-in. Read
[its guide](docs/hyprland-dms.md) first. Debian `homelab-dev` uses
`scripts/setup-homelab-dev.sh`, not the Arch workstation installer.
For a fast headless config update, run `bash scripts/link-home.sh homelab-dev`;
`--dry-run` and `--check` work there too.

## Validation and maintenance

```bash
python3 scripts/check-config.py
bash scripts/audit-system.sh laptop
```

The check requires Python 3.11+, Bash, shellcheck, Git, SSH, rsync, and tmux.
It validates shell/Python syntax, JSON/TOML, package list formatting, shellcheck,
and deployment into temporary homes for both workstation and the headless profiles.
It tests SSH settings, Bluetooth system-file backups, DMS initialization, package
journaling and rollback, repeated runs, previews, and package-failure handling. It does
not validate PAM behavior, display sessions, remote hosts, or package availability.

[GitHub Actions](.github/workflows/validate.yml) runs the same check on relevant
pushes and pull requests, or manually. It uses a hosted runner and read-only
repository permissions; it needs no machine credentials or homelab connection.
It becomes active when the workflow is committed and pushed.
See [GitHub's workflow reference](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
for the triggers and permission model.

The audit writes ignored reports under `reports/<machine>/`: installed packages,
enabled services, missing desired packages, explicit packages outside the
profiles, and link drift. Review `unlisted.txt` before deciding whether software
belongs in a package profile; it is never a removal list. Installed names may
also differ from selected providers, such as `nodejs-lts-*` versus `nodejs`.

For everyday changes: edit the repo, run the check, preview and apply links,
verify the affected app, then commit when ready. After Syncthing delivers the
changes to another host, rerun its linker if new paths were added. Avoid editing
the same files on two machines simultaneously; Syncthing handles transfer while
Git provides review and history. No automatic deployment workflow is needed.

## Coverage and remaining gaps (reviewed 2026-10-02)

The repo is a practical home for curated configuration and the agent kit.
It is not yet a complete backup or a one-command reconstruction of either host.

| Area | Coverage / next step |
| --- | --- |
| Shell, editor, terminal, agent kit | Deployable with the linker; Nord provides an Alacritty fallback before DMS generates its theme. |
| Workstation packages | Official/AUR lists corrected; Tailscale, printing, Moonlight, npm and terminal fonts included. AusweisApp now uses the [official package](https://archlinux.org/packages/extra/x86_64/ausweisapp/). Legacy Synergy needs a separately reviewed source. |
| Hyprland/DMS | Config, custom theme, plugin and helpers included. Curated defaults and plugin layout are initialized on first setup; existing theme preferences survive reruns; output rules describe the laptop and Wacom displays and are not a desktop display profile. |
| DWM / Rofi | `~/.xinitrc` depends on the external `~/dwm` checkout, its display/wallpaper/idle/suspend scripts and local picom config. Stored Rofi config references missing `rofi-*.sh` helpers and a missing powermenu theme. Capture those sources before calling desktop restore complete. |
| Application settings | Browser preferences included. Generated GTK palettes and DMS runtime settings stay local; stored GTK files are snapshots. KDE shortcuts, academic tools/TeX, and creative-app presets are not fully captured. The laptop profile now targets the verified AMD GPU, and `packages/study.txt` captures its optional academic/TeX tools. Add only settings you intentionally want to restore, and optional package lists for heavy workloads. |
| SSH / services | The linker installs SSH includes and the T3 PATH drop-in. T3 owns its generated base unit: with its CLI installed, run `t3 service install`, then reload user units. Provider logins and pairing remain local. |
| System changes | PAM/greeter have focused scripts. Install the stored Bluetooth workaround with `bash scripts/install-bluetooth-config.sh`; `--dry-run`/`--check` are supported, and existing system files are backed up. It does not reload hardware or reboot. Network profiles, firewall rules, backups and boot setup need separate review. |
| AUR build recipes | Recipe files are tracked directly by the parent repo; existing nested Git metadata stays local. No gitlinks or submodules are needed in a fresh clone. Optional GPU builds remain separate and require an online desktop; they were not rebuilt during this review. |
| Version control | The deployment sources, agent kit, tests and AUR recipes are versioned. Other sessions may still have local edits; Git preserves committed recovery points and Syncthing transports live edits. |

Keep SSH private keys, Bitwarden data, browser/mail profiles, provider logins,
chat databases, NetworkManager secrets and Syncthing identity local. Restore
those through existing backup/credential procedures. Do not sync whole app
state directories just to capture a few settings.

The linker adds the workstation/homelab SSH includes; the headless profile also
adds its GitHub-key fragment. Keys themselves are never copied into the repo.
For an SSH config managed by another symlink, add these directives to its source
at global scope instead:

```sshconfig
Include ~/Documents/config/ssh/workstations.conf
Include ~/Documents/config/ssh/homelab.conf
Host *
```

The GitHub key fragment is specific to `homelab-dev` and installed by its setup
script. The existing desktop was offline during this review; desktop runtime
and remote deployment have not been verified.

## Repo Layout

```
config/
├── packages/
│   ├── common.txt          # pacman packages on both machines
│   ├── laptop-kde.txt      # KDE Plasma + laptop-specific
│   ├── desktop-dwm.txt     # DWM + desktop-specific
│   ├── hyprland-dms.txt    # Optional Hyprland + DMS (additive)
│   ├── aur-common.txt      # AUR packages on both
│   ├── aur-desktop.txt     # Desktop-only AUR
│   ├── aur-laptop.txt      # Laptop-only AUR
│   └── remove-desktop.txt  # Packages removed during PC cleanup
├── home/
│   ├── .zshrc              # ZSH loader (sources ~/.config/zshrc/*.zsh)
│   ├── .gitconfig          # Git config
│   ├── .xinitrc            # DWM startup (desktop only)
│   ├── .Xresources         # X11 resources (desktop only)
│   └── .config/
│       ├── hypr/           # Hyprland + DMS (optional session)
│       ├── zshrc/          # ZSH modules (00-init, 10-options, 20-aliases, ...)
│       ├── zshrc.d/        # Per-hostname ZSH overrides
│       ├── alacritty/      # alacritty.toml (base) + laptop.toml / desktop.toml
│       ├── fastfetch/      # Fastfetch config
│       ├── starship.toml   # Starship prompt (Nord theme)
│       └── nvim/           # Neovim config (kickstart.nvim) — synced via Syncthing
├── agent/                  # Personal AI kit and machine context
│   ├── README.md
│   ├── AGENTS.template.md  # Minimal project AGENTS.md starter
│   ├── philosophy.md
│   └── skills/             # Linked into ~/.agents/skills/ by install-agent-kit.sh
├── scripts/
│   ├── install.sh          # Packages/services on an existing Arch installation
│   ├── install-hyprland-dms.sh  # Additive Hyprland+DMS trial
│   ├── remove-hyprland-dms.sh   # Undo Hyprland+DMS packages
│   ├── link-home.sh        # Symlink config files from repo into $HOME
│   └── audit-system.sh     # Generate package/service reports
└── docs/
    ├── hyprland-dms.md     # Hyprland + DMS trial / rollback
    └── system-manifest.md  # Historical system inventory
```

## ZSH Config Modules

| File | Purpose |
|---|---|
| `00-init.zsh` | XDG dirs, PATH, EDITOR, colors |
| `10-options.zsh` | Shell options, history, completions |
| `20-aliases.zsh` | All aliases (modern CLI, navigation, git, docker, etc.) |
| `30-functions.zsh` | Shell functions (extract, svim, gcom, lazyg, etc.) |
| `40-prompt.zsh` | Starship init |
| `50-tools.zsh` | zoxide, fzf, fastfetch, GitHub CLI completions |

Machine-specific overrides go in `~/.config/zshrc.d/<hostname>.zsh`.

## Syncthing Folders

| Folder | Direction |
|---|---|
| `~/Documents/` | ↔ bidirectional (ignores `/config` via `.stignore`) |
| `~/Projects/` | ↔ bidirectional |
| `~/Documents/config/` | ↔ bidirectional |

`~/.config/nvim/` and `~/.config/alacritty/` are NOT separate Syncthing folders
anymore — they are symlinked into this repo by `link-home.sh` and sync as part
of the `config` folder. Never sync a path via Syncthing that is also a symlink
into this repo (it creates self-referencing symlink loops).

`~/Documents/.stignore` on each machine must contain `/config` so the nested
config repo isn't double-synced (`.stignore` files are per-device, not synced).

## Agent kit (letter + skills)

`agent/` holds personal instructions, a collaboration letter, shared skills,
and [Fleet documentation](agent/fleet/README.md) for working with AI and managing
machines. See the Fleet guide for the research behind it, machine records,
daily workflow, and onboarding.

Run `bash scripts/install-agent-kit.sh` to install only AI context and skills;
`--dry-run` previews changes and `--check` verifies local readiness. Shared
instructions use one `agent/GLOBAL.md` source in every tool. The whole skills
directory is linked into `~/.agents/skills/` for Codex and OpenCode,
with per-skill compatibility links for Claude. The full
`link-home.sh` includes this step. Source files sync through this repo;
authentication, application state, and chats stay machine-local.

## Manual Steps After Install

1. **Syncthing**: Visit `http://localhost:8384`, add the other machine's device ID
2. **Neovim**: Run `nvim` — lazy.nvim auto-installs plugins on first launch
3. **Docker**: Log out and back in for group membership to take effect
4. **Fonts**: The machine package lists install MesloLGS Nerd Font (laptop) or JetBrainsMono Nerd Font (desktop)
5. **DWM** (desktop only): Build from `~/dwm/` or clone from `git.suckless.org/dwm`
6. **Agent skills**: Run `bash scripts/install-agent-kit.sh --check` and verify skills in a new session
