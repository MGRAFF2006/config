# Wispr Flow on the laptop

This is the [unofficial Linux port](https://github.com/wispr-flow-linux/wispr-flow-linux),
repackaged through the upstream AUR `wispr-flow-appimage` recipe. The proprietary
application still uses Wispr's account and cloud service.

Local package release 7 keeps the upstream download and SHA-256 check and repairs:

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
  whole canvas. Python and python-xlib are declared runtime dependencies.
- Hyprland window selection: in 0.57.0, floating XWayland windows are picked by
  their whole rectangle, even outside their input shape. An X11-only underlay
  test missed this; clicks to native Wayland windows were still blocked. The
  bundled `wispr-hypr-input.cpp` plugin checks the committed surface input region
  during window selection and skips excluded Wispr indicator/menu windows for
  that one synchronous query. It preserves configured focus rules and does not
  change geometry or painting. The Hub and other applications are unaffected.
- Overlay input on Hyprland: the launcher defaults to XWayland, as recommended
  by [upstream troubleshooting](https://github.com/wispr-flow-linux/wispr-flow-linux/blob/main/docs/troubleshooting.md#clicks-near-the-status-pill-are-swallowed-or-the-pills-buttons-dont-respond-on-wayland).
  The transparent canvas can then use X11 input shaping. Text injection retains
  the Wayland helper path. `WISPR_USE_WAYLAND=1` or `WISPR_USE_X11=0` explicitly
  overrides this default.

Build as the normal user:

```sh
cd ~/Documents/config/packages/aur-builds/wispr-flow-appimage
SRCDEST="$HOME/.cache/yay/wispr-flow-appimage" makepkg -fsi
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

When the local package is installed, the same Lua fragment loads its compositor
plugin. The build requires GCC, pkgconf and Hyprland headers; other desktops do
not load it. Its exact ABI check refuses a different Hyprland/core-library
version. Rebuild this local package after upgrading Hyprland or its core
libraries; the running compositor must match the installed headers. The plugin
is specific to the hit-test API tested here, so a future compositor change may
also require a source update.

To disable only the compositor workaround in a running session:

```sh
hyprctl plugin unload /opt/wispr-flow-appimage/usr/lib/wispr-flow/resources/Release/wispr-hypr-input.so
```

The next config reload loads it again while the Lua fragment is enabled.

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

The actual XWayland application was also launched inside isolated Hyprland
0.57.0, with a native GTK/Wayland window beneath it. A virtual pointer connected
only to that private compositor reproduced the missing click-through before
loading the plugin; the same click reached the native window afterward. Clicks
on the marked control still reached the actual Electron renderer. These checks
passed with the compiled plugin extracted from package release 7.

Additional checks covered two overlapping pinned overlays (a shaped X11 menu
fixture over the actual Status window), clicks inside each control, empty input
regions, and 30 region updates. Wispr's 512×614 viewport, position and painted
region stayed unchanged, with no renderer resize events. The menu fixture
verifies selection between overlays; it does not prove every real account menu.

Mathis confirmed that the input-only repair stopped the flickering and kept
controls clickable, but transparent space still blocked clicks. Release 7's
compositor fix is now loaded in the live session, with no config errors;
package verification reports no altered files. Live user confirmation of this
last click-through fix is pending. The existing Wispr process was retained.
Dictation was not exercised as part of this popup repair.

Updates normally come from AUR. Check whether newer recipes retain these fixes
before replacing this local build. No proprietary bundle or account data is
stored in the config repository.

## Show only during use

In Wispr Settings → System, turn off **Show Flow Bar at all times** to hide the
resting bar. The laptop uses that native preference (`hideFlowBarPermanently`);
the package does not change the default for other profiles. Recording and
processing still use the bar, and an active Notetaker meeting may keep it shown.
