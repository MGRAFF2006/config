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
cd ~/Documents/config
bash scripts/install-hyprland-dms.sh laptop --dry-run
bash scripts/install-hyprland-dms.sh laptop
# Optional: apply the laptop camera/PAM/greeter files explicitly.
# bash scripts/install-hyprland-dms.sh laptop --with-greeter
```

Then **fully log out** (Leave → Log out — not Lock, not Switch user).
At your existing login manager pick **Hyprland**. Plasma stays listed.
The default installer does not switch display managers or modify PAM.
The `--with-greeter` option installs the managed laptop PAM and greetd files;
review them before enabling greetd or disabling the current display manager.

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

First setup seeds a calmer **Nord** custom theme and `scheme-neutral`. Existing
theme selections are preserved when the installer runs again:

- `~/.config/DankMaterialShell/theme_nord.json`
- `settings.json` → `currentThemeName=custom`, `matugenScheme=scheme-neutral`
- Alacritty loads Nord as a fallback before DMS generates its terminal palette

To change later: Super+, → Theme, or swap `theme_nord.json` / matugen scheme.

| Keys | Action |
|------|--------|
| Super+Space / Super+R | App launcher |
| Super+A | Quick Settings — generic gear button stays in the bar |

### Dedicated bar panels

`networkDiagnostics` is a local DMS plugin linked from
`home/.config/DankMaterialShell/plugins/`. Apply the bar layout with:

```bash
python3 scripts/configure-dms-bar-panels.py --init
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
and back on when opened. `scripts/link-home.sh laptop` links the unit; enable the desired behavior with
`systemctl --user enable laptop-lid-awake.service`. Manual sleep remains available in the power menu. Suspend before
putting the laptop in a bag; closing the lid alone leaves it fully awake.

Legacy DMS 1.5.x shell overrides (only when that version exposes its QML files):

```bash
~/Documents/config/scripts/install-dms-shell-overrides.sh
dms restart
```

These patches are version-specific and are not part of normal installation.
Recent DMS packages embed QML and may leave only old patched files under
`/usr/share/quickshell/dms`; the presence of that directory alone is not proof
that patching it will affect the running shell.

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

Howdy needs a working `python-dlib`. Rebuild it against current libraries if
its import fails after an upgrade. The PAM installer checks the import before
changing authentication files; it no longer creates library ABI compatibility
symlinks automatically. `fix-howdy-libjxl.sh` is a legacy, version-specific workaround.
Verify face auth from a real session: `sudo howdy test`.

Greeter: **greetd + DMS greeter**. Plasma stays selectable. Rollback DM: `dms greeter uninstall`.

Full DMS defaults live in [`home/.config/hypr/dms/binds.lua`](../home/.config/hypr/dms/binds.lua).
DWM-style tags: [`home/.config/hypr/dms/workspaces.lua`](../home/.config/hypr/dms/workspaces.lua) + vendored `hyprsplit/`.
DWM-style extras: [`home/.config/hypr/dms/binds-user.lua`](../home/.config/hypr/dms/binds-user.lua).

## Rollback

**Soft (keep packages):** log out → choose **Plasma** at the greeter.

**Package rollback:** first log into Plasma/DWM, then preview and remove only
packages introduced by the optional-session installer:

```bash
bash scripts/remove-hyprland-dms.sh --dry-run
bash scripts/remove-hyprland-dms.sh
```

The installer records new packages in
`~/.local/state/config/hyprland-dms-packages.txt` before package transactions,
so a failed/partial installation can still be reviewed and rolled back. Reruns
retain the original record. Shared packages already installed for Plasma stay.
The remover retains settings and links, and refuses to remove a running
Hyprland session or an active/enabled greetd login manager. Restore the fallback
login manager and review `/etc/pam.d/*.backup-*` before removing a managed greeter.

Installations made before package recording have no trustworthy removal list;
the remover deliberately requires manual package selection in that case. A soft
rollback by selecting Plasma/DWM works without any package removal.

## Promote to desktop (later)

1. Run `bash scripts/install-hyprland-dms.sh desktop` (Syncthing already has the configs).
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
