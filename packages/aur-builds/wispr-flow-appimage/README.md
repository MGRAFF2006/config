# Wispr Flow on the laptop

This is the [unofficial Linux port](https://github.com/wispr-flow-linux/wispr-flow-linux),
repackaged through the upstream AUR `wispr-flow-appimage` recipe. The proprietary
application still uses Wispr's account and cloud service.

Local package release 6 keeps the upstream download and SHA-256 check and repairs:

- Root-only directories: installed directories use mode 0755.
- The bundled Electron sandbox: `chrome-sandbox` is root-owned mode 04755.
- Clipped popovers: the port's `WISPR_LINUX_STATUS_COMPACT` patch forces a
  200×110 viewport, while the calendar hover card alone is 400×154. The guarded
  `repair-overlays.py` disables that compact branch, restoring the app's normal
  bottom canvas (512×614 in the tested configuration). It preserves ASAR entry
  lengths and offsets and updates the SHA-256 integrity metadata.
- Control hit-testing: the screenshot/alpha path fails with `UnknownVizError`
  on this laptop. The repair enables the existing renderer-reported control and
  visual rectangles for Linux/XWayland, uses the existing native shape controller,
  and bypasses the failing alpha poll. A small persistent Python/Xlib helper
  applies only the X11 **input** region; the painted/bounding region stays intact.
  Changing the painted shape caused flickering under Hyprland and was rolled
  back. Empty reports produce an empty input region rather than exposing the
  whole canvas. This keeps buttons interactive and passes unused-space clicks
  through. Python and python-xlib are declared runtime dependencies.
- Overlay input on Hyprland: the launcher defaults to XWayland, as recommended
  by [upstream troubleshooting](https://github.com/wispr-flow-linux/wispr-flow-linux/blob/main/docs/troubleshooting.md#clicks-near-the-status-pill-are-swallowed-or-the-pills-buttons-dont-respond-on-wayland).
  The transparent canvas can then use X11 input shaping. Text injection retains
  the Wayland helper path. `WISPR_USE_WAYLAND=1` or `WISPR_USE_X11=0` explicitly
  overrides this default.

Build as the normal user:

```sh
cd ~/Documents/config/packages/aur-builds/wispr-flow-appimage
SRCDEST="$HOME/.cache/yay/wispr-flow-appimage" makepkg -si
wispr-flow --doctor
```

When replacing the original broken package, pacman preserves existing directory
permissions. Repair those once after installing this recipe:

```sh
sudo find /opt/wispr-flow-appimage -type d -exec chmod 755 {} +
```

Quit Wispr Flow from its tray menu and reopen it after updating; an existing
process keeps the previous renderer/backend. State and authentication remain
machine-local in `~/.config/Wispr Flow/`.

## Hyprland integration

`home/.config/hypr/dms/wispr-flow.lua` floats and pins `Flow Status Indicator` and
`Flow Context Menu`, removing compositor blur, borders and shadows. It permits
deliberate interaction and leaves window size and position to Wispr itself. The
Hub keeps normal tiling. The former geometry timer and focus-blocking rule were
removed: moving a clipped viewport cannot repair its contents.

The desktop entry is `/usr/share/applications/wispr-flow-appimage.desktop`.
`--doctor` warns about a missing entry because it checks another filename.
The laptop already has the required input group, uinput access and clipboard
utilities; no extra udev rule was needed.

## Verification

In separate actual-app profiles, the original renderer reported a 200×110
viewport with a 400×154 calendar card extending outside it. With the repair,
the actual app reported a 512×614 viewport containing the complete card bounds.
The unauthenticated test profile kept that card hidden, so the geometry check
did not prove its visible interactive state.

An actual-app X11 input test used a disposable profile and added one marked
button to the real status renderer. The renderer observer reported its bounds
and the native input region became exactly 120×40 at the button position. A real XTest
pointer click reached that button; a click in the unused canvas reached a
separate underlying window. This exercised the real Electron IPC, native shape
and pointer delivery, without relying on a stand-in application.

The actual XWayland application was also launched inside isolated Hyprland.
Thirty control-region updates left its 512×614 viewport, position and painted
region unchanged, with no renderer resize events. This catches the geometry
feedback that the earlier X11-only check missed.

After the latest user-instance restart, live metadata confirmed XWayland,
pinning, stable 512×614 painted bounds and a separate 60×20 idle input region.
Package verification reported no altered files. Mathis confirmed full popup
visibility and, with the prior shape implementation, working buttons; final
confirmation of click-through and flicker-free behavior with the input-only
repair is pending.
Dictation was not exercised as part of this popup repair.

Updates normally come from AUR. Check whether newer recipes retain these fixes
before replacing this local build. No proprietary bundle or account data is
stored in the config repository.

## Show only during use

In Wispr Settings → System, turn off **Show Flow Bar at all times** to hide the
resting bar. The laptop uses that native preference (`hideFlowBarPermanently`);
the package does not change the default for other profiles. Recording and
processing still use the bar, and an active Notetaker meeting may keep it shown.
