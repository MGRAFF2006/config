# Hyprland + Dank Material Shell (trial)

Additive Wayland session on top of existing Plasma (laptop) and DWM (desktop).
Nothing is removed; log out and pick **Plasma** / use `startx` anytime.

## Status

| Machine | Intent |
|---------|--------|
| laptop  | Try Hyprland + DMS first (this machine) |
| desktop | Promote later if the laptop trial feels good; keep dwm/`startx` |

## Install (laptop)

```bash
~/Documents/config/scripts/install-hyprland-dms.sh
# AUR companions (filesystem search + calendar):
yay -S --needed - < ~/Documents/config/packages/aur-laptop.txt
```

Then **fully log out** (Leave → Log out — not Lock, not Switch user).
At the **DMS greeter** pick **Hyprland**. Plasma stays listed.

Your compositor config is already Lua (`~/.config/hypr/hyprland.lua`). The
greeter’s own mini-Hyprland must also use Lua (`/etc/greetd/dms-hypr.lua`);
otherwise Hyprland shows a “`.conf` will be removed” notice on the login screen.
Re-apply with:

```bash
~/Documents/config/scripts/fix-greetd-hypr-lua.sh
```

**Hyprland (uwsm-managed)** only works if `uwsm` is installed. DMS greeter
ignores `TryExec=`, so a missing `uwsm` bounced you straight back to the
greeter — the fix script disables that session entry when `uwsm` is absent.

If you only lock the screen or open another VT greeter while a session is still
on tty1, you can bounce back. Check with:

```bash
loginctl list-sessions
# look for an active user session on tty1 — that must be gone before Hyprland
```

DMS is started from Hyprland with `dms run -d` (see `hyprland.lua`).
`dms.service` stays **disabled** so it does **not** start under Plasma.

Optional debug session log (desktop entry **Hyprland (DMS debug)**):

```bash
ls -lt ~/.local/state/hypr/session-*.log | head
```

## Tone / saturation

DMS defaults to Material **purple** + `scheme-tonal-spot`, which looks very
saturated (neon borders, vivid terminal matugen palette).

This kit pins a calmer **Nord** custom theme and `scheme-neutral`:

- `~/.config/DankMaterialShell/theme_nord.json`
- `settings.json` → `currentThemeName=custom`, `matugenScheme=scheme-neutral`
- Terminal matugen templates disabled (your Nord Alacritty stays)

To change later: Super+, → Theme, or swap `theme_nord.json` / matugen scheme.

| Keys | Action |
|------|--------|
| Super+Space / Super+R | App launcher |
| Super+A | Quick Settings — generic gear button stays in the bar |

### Dedicated bar panels

`networkDiagnostics` is a local DMS plugin linked from
`home/.config/DankMaterialShell/plugins/`. Apply the bar layout with:

```bash
scripts/configure-dms-bar-panels.py
dms restart
```

The network panel shows a five-minute download/upload graph, live
router/internet ping, DNS lookup time, traffic, address/gateway/DNS/MAC
details, Wi‑Fi signal/link rate, and the current saved Wi‑Fi password
(intentionally always visible inside the opened panel).

Audio uses DMS's standard volume, output, and input controls directly against
PipeWire/WirePlumber. There are no persistent virtual sinks or automatic
per-application routes.

`bt-a2dp-claim.service` keeps an A2DP headset claimed and conditionally inhibits
logind's lid-close suspend while a Bluetooth audio device is connected.

On the laptop, `laptop-lid-awake.service` independently blocks lid-close suspend
throughout the graphical session. Hyprland turns only `eDP-1` off on lid close
and back on when opened. `scripts/link-home.sh laptop` installs and enables the
service. Manual sleep remains available in the power menu. Suspend before
putting the laptop in a bag; closing the lid alone leaves it fully awake.

Install the DMS shell overrides with:

```bash
~/Documents/config/scripts/install-dms-shell-overrides.sh
dms restart
```

Re-run after `dms-shell` pacman updates.

Zen consumes DMS's generated `~/.config/DankMaterialShell/zen.css` through its
default profile. The managed `user.js` keeps native Wayland/GPU defaults while
reducing session restore work and enabling DNS, connection, and link/page
prefetching. Nautilus is the graphical file manager, follows DMS's generated GTK
palette, and opens with `Super+E`. Dolphin remains available in Plasma. Reapply
profile/default-app integration with:

```bash
scripts/configure-dms-app-integration.py
```

Restart Zen after first applying the integration or after changing managed
preferences. DMS color changes are picked up from the generated stylesheet on
the next Zen restart.

WiFi: prefer **system** NetworkManager secrets (not KWallet). Helper:
`nm-wifi-system-secret "SSID"` for networks that still prompt.

| Super+1 … 9 | Tag N on **this** monitor only (hyprsplit; DWM-like) |
| Super+Shift+1 … 9 | Move window to tag N on this monitor |
| Super+U / Super+I | Next/prev used tag on this monitor |
| Super+Ctrl+H/L | Focus other monitor |
| Super+O / Super+Tab | Overview |
| Super+Shift+/ | Keybind cheatsheet |

### Root / polkit prompt

Elevation prompts (`pkexec`, package installs, etc.) use **DMS’s Quickshell
Polkit modal** — same theme as the control center, not `polkit-kde-agent` or
`hyprpolkitagent`. Hyprland startup stops `hyprpolkitagent` so DMS owns the bus.
Plasma still uses KDE’s agent when you log into that session.

Fallback only if DMS polkit breaks: set `DMS_DISABLE_POLKIT=1` and start
`hyprpolkitagent.service` again.

### Keyring + Howdy

Hyprland starts `hypr-kwallet.service` (`ksecretd` + `pam_kwallet_init`).
PAM (managed under `system/pam.d/`, install with
`scripts/install-pam-keyring-howdy.sh`):

| Stack | Role |
|-------|------|
| `greetd` | Password/PIN first, Howdy fallback; `pam_kwallet5` + `ksecretd` |
| `sddm` | Same order for Plasma (fixes “wallet password again” after login) |
| `dankshell` | Same on DMS lock (`lockPamExternallyManaged=true`) |
| `sudo` | Howdy first, password fallback (terminal) |
| `polkit-1` | Password-only for the graphical DMS elevation prompt |

Greeter/lock: correct PIN skips the camera. Terminal `sudo`: camera first. Graphical polkit prompts remain password-only.
Set `greeterPamExternallyManaged=true` so DMS does not rewrite `/etc/pam.d/greetd`.

**Typed login password** unlocks `kdewallet` only if the wallet password equals
the login password. **Face-only login** cannot unlock the wallet (no AUTHTOK) —
blank wallet password or a TPM bridge (howdy-tpm) if you want zero prompts.

Re-apply PAM after greeter/package changes:

```bash
~/Documents/config/scripts/install-pam-keyring-howdy.sh
```

Howdy needs `python-dlib`. If `howdy test` fails on `libjxl.so.0.11`, run
`scripts/fix-howdy-libjxl.sh` (or rebuild `python-dlib-git` with proxy off).
Verify face auth from a real session: `sudo howdy test`.

Greeter: **greetd + DMS greeter**. Plasma stays selectable. Rollback DM: `dms greeter uninstall`.

Full DMS defaults live in [`home/.config/hypr/dms/binds.lua`](../home/.config/hypr/dms/binds.lua).
DWM-style tags: [`home/.config/hypr/dms/workspaces.lua`](../home/.config/hypr/dms/workspaces.lua) + vendored `hyprsplit/`.
DWM-style extras: [`home/.config/hypr/dms/binds-user.lua`](../home/.config/hypr/dms/binds-user.lua).

## Rollback

**Soft (keep packages):** log out → choose **Plasma** at the greeter.

**Hard (remove Hyprland/DMS packages):**

```bash
~/Documents/config/scripts/remove-hyprland-dms.sh
# optional wipe of DMS settings:
# REMOVE_DMS_STATE=1 ~/Documents/config/scripts/remove-hyprland-dms.sh
```

Plasma packages and dwm on the desktop are never touched by these scripts.

## Promote to desktop (later)

1. Run the same `install-hyprland-dms.sh` on `desktop` (Syncthing already has the configs).
2. Prefer SDDM (or a Wayland session entry) for Hyprland; keep `~/.xinitrc` / dwm as fallback.
3. Re-check Sunshine / Looking Glass on Wayland before dropping dwm as daily driver.

## Layout in repo

```
packages/hyprland-dms.txt          # additive pacman list
home/.config/hypr/hyprland.lua     # main compositor config
home/.config/hypr/dms/             # DMS fragments (binds, outputs, …)
home/.config/systemd/user/hyprland-session.target
home/.config/systemd/user/hypr-kwallet.service
system/pam.d/{greetd,sddm,dankshell}
system/howdy/config.ini
scripts/install-hyprland-dms.sh
scripts/install-pam-keyring-howdy.sh
scripts/remove-hyprland-dms.sh
```
