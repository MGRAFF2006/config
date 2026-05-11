# humunkulud's Config

Single source of truth for both machines. Synced bidirectionally via Syncthing.

## Machines

| Hostname | Role | WM | Shell |
|---|---|---|---|
| `archlinux` | Desktop (stationary) | DWM | ZSH + Starship |
| `laptop` (your hostname) | Laptop (portable) | KDE Plasma | ZSH + Starship |

## Fresh Install Bootstrap

On a fresh Arch Linux install:

```bash
curl -sL https://raw.githubusercontent.com/MGRAFF2006/config/main/scripts/install.sh | bash
```

Or manually:

```bash
# Install git first
sudo pacman -S git

# Clone the repo
git clone https://github.com/MGRAFF2006/config ~/Documents/config

# Run the install script
~/Documents/config/scripts/install.sh
```

The script will ask you to choose `laptop` or `desktop` and handles everything:
- Installs yay (AUR helper)
- Installs all packages (common + machine-specific)
- Symlinks all config files
- Sets ZSH as default shell
- Enables systemd services (Syncthing, Docker, Bluetooth, etc.)

## Repo Layout

```
config/
├── packages/
│   ├── common.txt          # pacman packages on both machines
│   ├── laptop-kde.txt      # KDE Plasma + laptop-specific
│   ├── desktop-dwm.txt     # DWM + desktop-specific
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
│       ├── zshrc/          # ZSH modules (00-init, 10-options, 20-aliases, ...)
│       ├── zshrc.d/        # Per-hostname ZSH overrides
│       ├── alacritty/      # alacritty.toml (base) + laptop.toml / desktop.toml
│       ├── fastfetch/      # Fastfetch config
│       ├── starship.toml   # Starship prompt (Nord theme)
│       └── nvim/           # Neovim config (kickstart.nvim) — synced via Syncthing
├── scripts/
│   ├── install.sh          # Reproducible setup script (run on fresh Arch install)
│   ├── link-home.sh        # Symlink config files from repo into $HOME
│   └── audit-system.sh     # Generate package/service reports
└── docs/
    └── system-manifest.md  # Full system documentation
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
| `~/Documents/` | ↔ bidirectional |
| `~/Projects/` | ↔ bidirectional |
| `~/Documents/config/` | ↔ bidirectional |
| `~/.config/nvim/` | ↔ bidirectional |
| `~/.config/alacritty/` | ↔ bidirectional |

## Manual Steps After Install

1. **Syncthing**: Visit `http://localhost:8384`, add the other machine's device ID
2. **Neovim**: Run `nvim` — lazy.nvim auto-installs plugins on first launch
3. **Docker**: Log out and back in for group membership to take effect
4. **Fonts**: Ensure MesloLGS Nerd Font (laptop) or JetBrainsMono Nerd Font (desktop) is installed
5. **DWM** (desktop only): Build from `~/dwm/` or clone from `git.suckless.org/dwm`
