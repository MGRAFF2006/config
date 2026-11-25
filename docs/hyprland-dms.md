# Hyprland + Dank Material Shell (trial)

Additive Wayland session on top of existing Plasma (laptop) and DWM (desktop).
Nothing is removed; log out and pick **Plasma** / use `startx` anytime.

## Status

### Slow desktop after login while offline

On the laptop, private SSH waits for `tailscale-online.target`. Starting that
service directly from `multi-user.target` also delays services ordered after
that target, including the power-profile service queried by DMS during loading.
The 2026-11-03 startup log showed DMS taking 26 seconds to load while the
Tailscale wait held the boot target for 65 seconds.

For an existing Tailscale-ordered SSH setup, apply the focused migration:

```bash
bash scripts/install-ssh-startup.sh --dry-run
sudo bash scripts/install-ssh-startup.sh
bash scripts/install-ssh-startup.sh --check
```

The timer starts the same SSH service, retaining its Tailscale readiness check
and listener configuration, without holding up `multi-user.target`. It does not
restart SSH or the desktop, or change power profiles. Recheck after any setup
flow that directly enables `sshd.service` again.

To restore the previous direct boot start, run `sudo systemctl enable sshd.service`
then `sudo systemctl disable --now sshd-tailscale.timer`. This restores the wait
too. Previous timer files and enablement states are saved under
`/var/backups/config-ssh-startup/`.

### Session selection

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

The network panel uses DMS's live NetworkManager state for the connection
summary and bar icon. Its Networks tab provides the stock Wi-Fi/Ethernet
controls; Connection & diagnostics shows copyable IPv4/IPv6 details, traffic,
and separate router/public-IP/DNS measurements. Internet access comes from
NetworkManager's cached connectivity assessment for the whole device. Public-IP
and DNS probes follow the system route, including VPNs; router ping is bound
to the displayed interface. A missed ping is “No reply”,
not “Offline”; an unavailable DNS lookup is labelled separately. Unknown or
stale measurements never override the active connection. The helper samples
the displayed interface, clears traffic history on connection changes, and
refreshes without overlapping requests. It never retrieves Wi-Fi passwords.
Run `python3 scripts/check-dms-network-status.py` for the focused logic checks.

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
The installer applies only top-level `shell-patches/*.patch` files. Exact-version
DMS 2.x patches live in `shell-patches/guarded/` and are applied only by the
fingerprint-checked stager in [dms-smooth-sliders.md](dms-smooth-sliders.md).
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

OnlyOffice's default custom window frame includes invisible shadow padding
that leaves a large gap inside a Hyprland tile. Switch it to the system frame
once: save your documents, close OnlyOffice, then run
`onlyoffice-desktopeditors --system-title-bar`. OnlyOffice saves this choice
in its own settings, so later launches keep the system frame. Revert the same
way with `--custom-title-bar`. The integration script prints this reminder when
OnlyOffice is installed but never edits OnlyOffice's settings file. See the
[OnlyOffice window-frame flags](https://api.onlyoffice.com/docs/desktop-editors/usage-api/command-line-flags/).

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
| `sddm` | Password first, Howdy fallback for Plasma |
| `dankshell` | Password/PIN first, Howdy fallback; face starts on wake (DMS lock) |
| `sudo` | Howdy first, password fallback (terminal) |
| `polkit-1` | Password-only for the graphical DMS elevation prompt |

Greeter and lock ask for the password before Howdy, so a typed password never
waits for the camera, even when it hangs. Terminal `sudo` tries the camera
first. Graphical polkit prompts remain password-only.
Greeter: submit the empty password field to use your face.
Set `greeterPamExternallyManaged=true` so DMS does not rewrite `/etc/pam.d/greetd`.
For DMS 2.1, keep `lockPamExternallyManaged=true` and set
`lockPamPath=/etc/pam.d/dankshell`; otherwise it selects the distro `login` stack.
The installer (via `scripts/configure-dms-lock-pam.py`) edits
`$XDG_CONFIG_HOME/dms/settings.json`, the file DMS 2.1 reads, never the legacy
`~/.config/DankMaterialShell/settings.json`. It sets an empty `lockPamPath`,
keeps any custom one, and warns if DMS has not created its settings yet.
It refuses, before changing any PAM or Howdy file, when DMS might require a
security key: an externally managed lock makes DMS skip its own key step, and
`dankshell` has no `pam_u2f`, so the key would silently stop being required.
The check does not copy how DMS combines its settings. It reads `settings.json`,
every file in `dms/config.d` (hidden files and any name included), the
`/usr/share/dms` and `/etc/dms` `cli-policy.json`, `DMS_POLICY_LOCK_SETTINGS`
in the caller's environment (checked before `sudo`, which drops it) and in
the launch environment of the user's running DMS/Quickshell processes. It
refuses when any of them has, at any depth and in any letter case, a
security-key setting that is not clearly off: `enableU2f`, `greeterEnableU2f`
or `lockPamInlineU2f` other than `false`, `u2fMode` other than `"or"`, or a
non-empty `lockU2fPamPath` (`null` counts as off). So it can refuse where DMS
would not ask for the key, e.g. Alternative (OR) mode with the key on; remove
or turn off the listed settings (and restart DMS if a running process is
listed), then re-run. An input that is not strict JSON (invalid UTF-8,
`NaN`/`Infinity`, duplicate keys), or that cannot be read, including the
environment of a running DMS process, stops the installer and is named.
DMS's own fingerprint unlock is not offered with the managed stack either;
the installer warns when it is on.
The settings file is replaced atomically, keeping its mode and owner, and is
written before any PAM or Howdy file. If that step fails, the installer stops
with an error and changes no PAM or Howdy file. The error says whether
`settings.json` was already replaced: a failure to flush its directory after
the rename leaves the new settings in place. PAM files written after it are not
rolled back on a later failure; their `.backup-*` copies stay.

The guarded `howdy-lock-2.1.patch` starts one face attempt after the display
turns back on, after a resume from sleep, or after a key press or click on the
lock screen. Locking alone does not start the camera, so a manual lock with the
display on stays locked while you are still in front of it. A suspend that DMS
requested but that never happened (refused or inhibited) is not a wake either.
The attempt answers the managed stack's password prompt with an empty response,
which falls through to Howdy. When no face matches it ends silently, including
Howdy's "Failure, timeout reached" notice. Pressing Enter on the empty field
starts a face attempt, or keeps the running one, and reports its failure.
The password field keeps accepting keys during any face attempt: the first
typed key abandons it, and the password goes to a fresh attempt that never
reaches Howdy. The existing 15-second watchdog recovers a stalled camera when
nothing is typed. Abandoning an attempt kills only Quickshell's PAM helper.
Howdy's separate capture process (`compare.py`) can keep running until it
matches or reaches Howdy's `timeout` (default 4 seconds), or longer if the
camera driver stalls. A face attempt started meanwhile can fail while that
process still holds the camera; a correct password never reaches Howdy and is
unaffected. This is from the Quickshell and Howdy sources, not measured on the
laptop. The `dankshell` stack omits `nullok`,
and a face attempt that succeeds before its empty answer was sent stays
locked, so a blank Unix password never unlocks without a face match; an
account without a password unlocks the lock screen with the face only. Stage it through
`python scripts/configure-dms-smooth-sliders.py --apply` and use the staged UI
on the next shell start. Unknown DMS versions use the packaged UI and require
reviewing the patch again; manual Submit still starts PAM.

**Typed login password** unlocks `kdewallet` only if the wallet password equals
the login password. **Face-only login** needs the optional account-bound TPM
bridge to supply that token. It is held until boot and storage protection is
verified, and only `scripts/install-howdy-kwallet-tpm.py --apply
--boot-protection-verified` adds its step to greetd; the routine PAM install
below never does, and removes it again. The wallet remains encrypted;
missing/unavailable credentials retain manual password fallback. See
[hold, setup, security tradeoff and recovery](../packages/aur-builds/howdy-tpm/README.md).
This does not unlock independent application vaults such as Bitwarden.

Re-apply PAM after greeter/package changes:

```bash
~/Documents/config/scripts/install-pam-keyring-howdy.sh
```

The installer replaces `greetd`, `sddm`, `dankshell`, `sudo` and `polkit-1`
whatever they contain (each with a `.backup-<stamp>` copy), so it also applies
over a hand-edited password-only `greetd` or `dankshell`. It never edits
`system-auth`. Face unlock on the lock screen also needs the staged
`howdy-lock-2.1.patch`; with a password-only `dankshell` that patch stays
inactive.

Howdy needs a working `python-dlib`. Rebuild it against current libraries if
its import fails after an upgrade. The PAM installer checks the import before
changing authentication files; it no longer creates library ABI compatibility
symlinks automatically. `fix-howdy-libjxl.sh` is a legacy, version-specific workaround.
Verify face auth from a real session: `sudo howdy test`.

Greeter: **greetd + DMS greeter**. Plasma stays selectable. Rollback DM: `dms greeter uninstall`.

For an existing greeter whose colors, wallpaper or controls stopped matching the
desktop, use `python3 scripts/install-dms-greeter-theme.py --apply`. This repair
does not change PAM or restart the display manager. See [theme synchronization,
renderer compatibility and recovery](dms-greeter-theme.md).

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
