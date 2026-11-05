# Laptop

## Wispr overlay repair — verified 2026-11-05

Local `wispr-flow-appimage` release 7 restores the normal popup canvas and
uses renderer-reported X11 input regions without changing the painted shape.
Mathis confirmed complete popup visibility, clickable controls and stopped
flickering, but clicks through unused space still failed against native Wayland
applications. Hyprland 0.57.0 selected the whole XWayland rectangle regardless of
its input shape.

The bundled compositor plugin now honors the committed input region when
selecting Wispr indicator/menu windows. It leaves the Hub, configured focus
rules and window geometry alone. In isolated Hyprland, the actual Electron app
reproduced the failure before the plugin; afterward a virtual-pointer click
reached a native GTK/Wayland underlay, and Wispr's control still received clicks.
The packaged plugin also passed overlapping-overlay, empty-region and 30-update
geometry checks. It is loaded in the live session with no config errors, and
package verification found no altered files. User confirmation of this final
click-through change is pending. Rebuild the local package after compositor or
core-library upgrades; mismatched ABIs are refused.
See the [repair and verification details](../../../packages/aur-builds/wispr-flow-appimage/README.md).

The native **Show Flow Bar at all times** preference is off at Mathis's request:
the resting bar is hidden, with active-use visibility managed by Wispr. The
preference is stored only in the app profile.

## Wispr Flow installation — verified 2026-11-05

The unofficial native Linux port is installed as
`wispr-flow-appimage 1.0.5+wispr1.6.1337-7`. The upstream AppImage checksum
passed. The local package repairs root-only directories and sets the bundled
Chromium sandbox to root-owned mode 04755. Pacman's file verification reports
no altered files. See the [recipe and restore instructions](../../../packages/aur-builds/wispr-flow-appimage/README.md).

The application rendered its sign-in screen in the isolated agent desktop.
`wispr-flow --doctor` passes its required checks on the real Hyprland session,
including uinput, all input devices and clipboard tools. Its missing-desktop-entry
warning checks the wrong filename; the application menu entry is installed.
Accessibility is initially disabled and the helper enables it at runtime.
Dictation was not exercised by this installation check.

## Login-screen appearance — verified 2026-11-05

The DMS greeter now uses live per-account settings, wallpaper/session data and
colors. Its existing user service retains Gio file events while native
profile-only sync repairs read access; twelve rapid mode-0600 atomic session
replacements were repaired successfully. The greeter account can read the
root-owned guarded renderer and live theme inputs. The renderer adds support
for the desktop's fixed corner radius and popup transparency; unknown package
builds fall back to the packaged UI.

The actual patched greeter rendered in a private nested Hyprland session, and
theme readback matched the desktop palette, text scale, corners and opacity.
PAM fingerprints and the running greetd process stayed unchanged. A fresh
login/logout remains untested. Apply/recover through the
[greeter theme guide](../../../docs/dms-greeter-theme.md).

## Desktop startup dependency — verified 2026-11-04

Private SSH now starts through `sshd-tailscale.timer`, retaining its existing
Tailscale-online ordering and loopback/Tailscale listeners. Its direct
`multi-user.target` enablement was removed with
`scripts/install-ssh-startup.sh`; neither SSH nor the desktop was restarted.
Previously, the Tailscale wait held `multi-user.target` for 65 seconds and
prevented DMS's power-profile service from starting during shell loading.
The Quickshell log recorded a 26-second configuration load.

The live dependency graph no longer puts SSH below `multi-user.target`;
a controlled systemd check confirmed the timer lets the desktop target proceed
while the SSH readiness wait runs. Fresh agent SSH and unchanged listener/PID
checks passed. Power settings were not changed. A fresh boot/login has not been
measured. See [the migration and rollback](../../../docs/hyprland-dms.md#slow-desktop-after-login-while-offline).


## Readable wallpaper theming — verified 2026-11-03

Hyprland 0.57 / DMS 2.0 uses 2 px gaps with larger shell controls and 115%
text, small window corners, acrylic blur and fast subtle transitions. DMS's built-in
Material `garden` wallpaper is active with a cool accent selected in DMS; the previous
keyboard-reference wallpaper remains in `keyboards/corne/wallpaper.png`.

Apply the saved appearance with `scripts/configure-desktop-appearance.py --apply`
and toolkit integration with `scripts/configure-desktop-app-themes.py --apply`.
Both print local backups before changing settings. Initial task snapshots are
under `~/.local/state/config/desktop-refresh-2026-11-03/`. See
[appearance](../../../docs/desktop-appearance.md) and
[application theming](../../../docs/desktop-app-themes.md) for scope and recovery.

GTK3/4 use DMS's generated palette and adw-gtk3; Qt5/6 use the KDE platform
plugin (`plasma5-integration` / `plasma-integration`). Existing GTK font choices
are preserved. Alacritty, Zen, Neovim surfaces and VS Code share palette exports. Folder/place icons use generated local Papirus
overlays; application icons remain inherited.
Native Qt5/Qt6 and GTK3 palette queries matched generated background/text/accent;
Neovim's actual Normal highlight matched too. An automatic image change and
return to the Material wallpaper regenerated the palette/hook. Existing apps
may require reopening; self-rendered interfaces and web content remain app-specific.
Only the isolated compositor was captured for visual checks.

The per-monitor tag dispatcher also now recognizes `0` as disabled for
`binds.workspace_back_and_forth`. The original code toggled to the previous
tag because Lua treats zero as true. The isolated compositor reproduced
`2, 3, 3` ending on 2 before the fix and 3 afterward; local tag mapping is retained.


## Personal-file sync — verified 2026-10-25

Syncthing now carries personal Documents, Downloads, Pictures, Music, Videos
and Calibre Library. Projects and this config/agent-kit checkout use Git;
their sync registrations were removed with local files preserved. Known
software roots inside Documents and generated caches are excluded. Apply or
preview through `scripts/configure-personal-sync.py`; see
[scope and recovery](../../../docs/personal-sync.md). The desktop was offline
during migration and needs the same setup when reachable. Uncommitted config
edits no longer propagate automatically between machines.

Portable interactive workstation. User: `humunkulud`; OS: Arch Linux;
Tailscale identity: `laptop` (`100.66.24.27`). Use the established Tailscale name
for connections. The local hostname alone does not identify this device.

## Capabilities

Ryzen AI 7 350, Radeon 860M integrated GPU, about 30 GiB usable RAM. Prefer it for
interactive coding, research, review, and light checks. Battery, heat, travel,
and suspension matter more than its memory capacity. There is no locally
configured model runtime in this kit; cloud coding agents use their provider.

Verified on 2026-10-02: current session is Hyprland on Wayland. KDE Plasma is
also part of the documented setup; do not assume which session is running.

## AI tools and supporting services

Verified on 2026-10-02:

| Component | Observation |
| --- | --- |
| Codex on PATH | `~/.npm-global/bin/codex`, CLI version `0.160.0` |
| Arch Codex package | `openai-codex 0.155.1-1`; differs from the PATH executable |
| OpenCode on PATH | `~/.opencode/bin/opencode`, version `1.18.25` |
| Arch OpenCode package | `opencode 2.0.12-1`; differs from the PATH executable |
| T3 Code | `t3code-bin 0.0.38-1`, launched through `~/.local/bin/t3code` |
| Thunderbird MCP | Add-on 0.9.2 enabled; authenticated API verified on `127.0.0.1:8765` (40 tools). Source: `~/Projects/thunderbird-mcp`; Codex registration: `scripts/configure-thunderbird-mcp.sh`. Connection tokens stay machine-local. |
| Cursor | Desktop app and CLI uninstalled on 2026-10-02; removed from the package list and agent-kit installation targets |
| Supporting tools | Git, gh, SSH, rsync, tmux, Node, Bun, Python, shellcheck available |
| Tailscale | `tailscaled` active |
| Syncthing | User service active; `Documents/config` is a configured share |
| Agent kit | Installed; readiness check passed; OpenCode discovered the six initial shared skills; the shared kit now also includes ponytail |
| Codex authentication | CLI login status detected an authenticated session; no credentials copied |

If behavior differs from package documentation, check `command -v codex`,
`command -v opencode`, and their `--version` output first. Do not delete or
replace either installation without a concrete reason.

## Connections and paths

- Config and Fleet: `~/Documents/config/agent/`.
- Personal work: `~/Documents/`; software under `~/Projects/` uses independent Git checkouts.
- Desktop: `ssh desktop`; SSH configuration resolves to `100.65.78.19`, user
  `humunkulud`, port 22. Reachability was not available during setup.
- T3 launcher and campus proxy source: `home/.local/bin/t3code` and
  `home/.config/t3code-proxy/` in the config repo. The campus relay workaround
  depends on desktop reachability. Diagnose that dependency if it fails.
- Leave provider logins, SSH private keys, T3 connection catalogs, and agent
  session databases machine-local.

## Lid close and recovery

Configured on 2026-10-02 at Mathis's explicit request: `laptop-lid-awake.service`
blocks logind's lid-close suspend during the graphical session. Hyprland turns
the built-in `eDP-1` display off on lid close and on when opened. Manual sleep
remains available; suspend before putting the awake laptop in a bag.

A local tmux session does not prevent manual suspension, and a graphical agent
thread may lose its connection after sleep. When back, reopen/reconnect the app,
inspect `git status`, check any running processes, and tell the agent to resume
from the existing work.

If a task must continue while this laptop sleeps, use the desktop when it is
online and keep the job in tmux **on the desktop**.
