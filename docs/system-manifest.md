# System Manifest - humunkulud's Arch Linux

Generated: 2026-05-04
Machine: Laptop (archlinux)

## System Overview

- **OS:** Arch Linux (rolling)
- **Desktop:** KDE Plasma 6 (Wayland)
- **Shell:** bash + starship prompt
- **Terminal:** Alacritty
- **Editor:** Neovim (kickstart.nvim)
- **GPU:** AMD (ROCm/HIP for ML) + Intel (media decode)
- **Init:** systemd, SDDM display manager

---

## Package Categories

### Core System
```
base base-devel linux linux-firmware amd-ucode
grub efibootmgr dosfstools btrfs-progs
networkmanager iwd wireless_tools
bluez bluez-utils
pipewire pipewire-alsa pipewire-jack pipewire-pulse wireplumber
libpulse gst-plugin-pipewire
alsa-firmware alsa-utils sof-firmware
power-profiles-daemon zram-generator smartmontools
```

### Desktop Environment (KDE Plasma)
```
plasma-meta plasma-workspace
dolphin ark kate konsole
kdeconnect
network-manager-applet
sddm (via plasma-meta)
xdg-utils xorg-xinit
```

### GPU / Graphics Drivers
```
xf86-video-amdgpu
vulkan-radeon lib32-vulkan-radeon
vulkan-intel vulkan-nouveau
intel-media-driver libva-intel-driver
```

### Development Tools
```
git github-cli
base-devel (gcc, make, etc.)
docker docker-compose
python-pip
bun
```

### Terminal / CLI Tools
```
alacritty
bat btop htop fzf tree ncdu wget
fastfetch nano screen picocom
man-db man-pages bash-completion
reflector
```

### Editors / IDEs
```
vim (legacy, can remove)
visual-studio-code-bin (AUR)
obsidian
opencode
```

### Web Browsers
```
chromium
zen-browser-bin (AUR)
```

### Communication
```
discord
teams-for-linux (AUR)
thunderbird
zoom (AUR)
```

### Media / Creative
```
obs-studio
vlc
audacity
gimp
krita
blender
sox
```

### 3D Printing / Photogrammetry
```
orca-slicer-bin (AUR)
superslicer-bin (AUR)
meshroom (AUR) + alice-vision (AUR)
```

### Gaming
```
steam
prismlauncher (Minecraft)
moonlight-qt (game streaming)
satisfactory-mod-manager (AUR)
```

### Documents / Office
```
calibre
texlive-* (full LaTeX installation)
anki
cups cups-browsed cups-pdf system-config-printer
```

### AI / ML (ROCm Stack)
```
rocm-hip-sdk rocm-ml-sdk rocm-ml-libraries rocm-opencl-sdk
hip-runtime-amd hipblas hipcub hipfft hipsolver hipsparse
miopen-hip rccl rocalution rocrand rocthrust roctracer
rocm-cmake rocm-dbgapi rocm-gdb rocm-smi-lib rocminfo
dlib-cuda
ollama-vulkan
```

### Security / VPN / Privacy
```
bitwarden
mullvad-vpn-bin mullvad-vpn-daemon-bin (AUR)
wireguard-tools
ausweisapp2 (AUR, German eID)
```

### Utilities
```
qbittorrent
scrcpy (Android screen mirror)
localsend-bin (AUR, local file transfer)
balena-etcher (AUR, USB flashing)
gearlever (AUR, AppImage manager)
youtubedownloader (AUR)
uxplay (AirPlay receiver)
pdfmerger (AUR)
wl-clipboard
```

### Misc / Niche
```
goodnotes-electron (AUR)
spotify (AUR)
snapchat (AUR, via libelectron)
putty
evtest libinput-tools
jupyter-notebook
ladybird (AUR, experimental browser)
```

### AUR Build Dependencies (installed as explicit but are build helpers)
```
python-cmake
vcpkg-git
extra-cmake-modules-git
yay
trash
wakatime
t3code-git
```

---

## Enabled Services

### System
- NetworkManager, bluetooth, cups, docker
- mullvad-daemon, ollama
- sddm, systemd-resolved, systemd-timesyncd

### User
- pipewire, pipewire-pulse, wireplumber

---

## Non-pacman Software

### npm (global, in ~/.local)
- neovim (node provider)
- tree-sitter-cli

### pip (user)
- pynvim, PyMuPDF, greenlet

### Flatpak
- Hytale Launcher

### Manual installs (~/.local/bin)
- neovim (AppImage-style tarball)
- zoxide
- opencode CLI (~/.opencode/bin)

---

## Config Files to Sync (dotfiles)

These define your work environment:
```
~/.bashrc
~/.inputrc
~/.gitconfig
~/.config/alacritty/
~/.config/nvim/
~/.config/starship.toml
~/.config/opencode/     (if exists)
~/.ssh/config           (create for PC)
```

---

## Orphaned Packages to REMOVE

These are build-time dependencies or leftover from removed packages.
They are NOT required by anything currently installed.

### Safe to remove (pure build tools, no runtime use):
```
ant autoconf-archive doxygen gendesk gi-docgen gperf gtk-doc
icoutils inotify-tools jq meson mold nasm patchelf pkgfile
python-flit-core python-hatch python-maturin python-nose
python-pyflakes python-scikit-build-core python-setuptools-scm
ragel reuse swig t1utils tpm2-tools unifdef utf8cpp
wayland-protocols xbitmaps xorg-server-xvfb yarn
python-pyzstd python-requests-mock python-respx python-spur
python-pytest-asyncio python-pytest-cov python-pytest-mock
python-pytest-xdist python-freezegun python-coloredlogs
python-sphinx-furo moreutils net-tools range-v3 simdjson
go-task chrono-date qt5-tools qt6-doc mimalloc pnpm nvm
```

### Probably safe (manim deps, but manim not installed as package):
```
python-manimpango python-moderngl python-pyglm python-pyrr
python-pywavefront python-screeninfo python-skia-pathops
python-svgelements python-isosurfaces python-cloup python-trimesh
python-glcontext python-mapbox-earcut python-multipledispatch
python-pyglet python-sounddevice python-cobble python-funk
python-precisely python-tempman python-srt python-standard-aifc
python-pdfminer python-pydub python-av
```
NOTE: If you still use manim, install it in a venv instead.

### Probably safe (meshroom/photogrammetry build deps):
```
cctag cereal cgal flann gklib libigl libe57format
metis nanoflann openmesh parallel-hashmap
```
NOTE: meshroom itself is still installed. Remove these only if you also remove meshroom.

### Probably safe (face recognition - not actively used?):
```
python-face_recognition python-face_recognition_models
python-dlib-git python-onnxruntime-cpu onnx
python-google-auth-oauthlib python-tensorboard_plugin_wit
```

### Probably safe (old/dead):
```
python2                  # Python 2 is dead since 2020
nodejs-nativefier        # Deprecated tool
electron36 electron38    # Old Electron versions, nothing uses them
dotnet-sdk               # Not required by anything
inkscape                 # Orphaned (was probably a dep of something)
go                       # Orphaned (no Go projects active)
openssl-1.1              # Legacy OpenSSL
slicer-udev              # Leftover from slicer
libkdcraw5 quazip-qt5    # Qt5 leftovers
kcompletion5 kcrash5 kguiaddons5 ki18n5 kitemviews5  # KDE5 leftovers
cantarell-fonts          # GNOME font
shc                      # Shell compiler, unlikely needed
```

---

## Packages to Consider Removing (explicitly installed but questionable)

| Package | Reason |
|---------|--------|
| `vim` | You use nvim now |
| `putty` | You have SSH built-in |
| `superslicer-bin` | Orca Slicer is newer/better |
| `snapchat` | Electron wrapper, rarely useful on desktop |
| `goodnotes-electron` | You switched away from Goodnotes? |
| `nodejs-nativefier` | Deprecated |
| `python2` | Dead language |
| `ladybird` | Experimental browser, not daily use |
| `sumatrapdf` | Windows PDF viewer (won't work on Linux?) |
| `wireguard-ui` | Web UI, do you use it? |

---

## Recommended Additions (for both machines)

```
sudo pacman -S eza fd lazygit git-delta duf dust tldr glow
```

---

## Syncthing Setup (for file sync between machines)

Install on both machines:
```
sudo pacman -S syncthing
systemctl --user enable --now syncthing
```

Recommended folders to sync:
- `~/Projects/` (code)
- `~/Documents/` (all docs)
- `~/.config/nvim/` (editor config)
- `~/.config/alacritty/` (terminal config)
- `~/.bashrc`, `~/.inputrc`, `~/.gitconfig` (via dotfiles repo or Syncthing)

Access Syncthing web UI at: http://localhost:8384
