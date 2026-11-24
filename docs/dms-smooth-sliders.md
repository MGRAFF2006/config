# Fast, subtle slider motion

The same guarded UI override also includes inline quick-access detail pages.
Opening network, Bluetooth, audio or other control-center details replaces the
tile grid on the existing panel surface. The panel fits its content within the
display bounds, with a Back button and the existing Escape/outside-dismiss
behavior. There is no centered second card, extra dimming layer or zoom effect.
Back returns to the tile grid. Device actions and nested device selectors retain
their existing behavior.

DMS 2.0's shared slider normally places its handle directly at each integer
volume or brightness value. Panel-opening motion does not interpolate that
progress. The `shell-patches/guarded/smooth-slider-level.patch` moves a
separate visual ratio with a critically damped tracker that covers 99% of a
step within about 110 ms. Held-key repeats keep the running velocity instead of
restarting an easing curve on every step. The handle never passes the target or
moves away from it; a reversal starts from rest. Qt's `SmoothedAnimation` was
not used because a close retarget while moving made it briefly run backwards
below the track. The real value, adjustment signal and hardware update remain
immediate. Pointer dragging, reduced motion and disabled animations bypass the
transition.

Launcher results use single-line native styled-text elision for both the title
and subtitle, preserving search emphasis. Display-only newline normalization
keeps multiline clipboard entries within their rows; the full name, clipboard
payload and accessible label remain unchanged. Plain `dms dmenu` rows keep
their generated search emphasis and elide the same way; only rows from
`dms dmenu --markup-rows` keep explicit rich HTML with wrapping, so their CSS
font sizes survive. The guarded patch set also fingerprints `LauncherRow.qml`
before applying this correction.

Check the launcher rows against pristine DMS UI input:

```bash
python3 scripts/check-dms-launcher-text.py --source-dir PRISTINE_DMS_UI
python3 scripts/check-dms-launcher-text.py --source-dir PRISTINE_DMS_UI --unpatched  # reproduces the overflow
```

It stages the override into a temporary directory, checks that the launch
guard falls back when any patched renderer or the version changes, and runs
the actual launcher components with synthetic clipboard, app and dmenu entries:
rows at 620/320 px, and on 2.1.2 also grid tiles at 180/120 px and image
captions; highlighted and multiline entries, long subtitles, short app labels,
searched plain dmenu rows, explicit dmenu HTML, 115% text scale and unchanged
payloads. DMS's components need a real window backend, so the fixture runs on
a private Xwayland inside a headless KWin, both in bubblewrap with a read-only
root, throwaway HOME and `/tmp`, private D-Bus and no network. It needs
`bwrap`, `kwin_wayland`, `Xwayland` and `qs`; nothing reaches the running
desktop, its settings or the clipboard. Without `--source-dir` it stages from
the running shell's `dms.path` (under `XDG_RUNTIME_DIR`), like the configure
helper. It first copies that input into private storage, replacing symlinks
with their contents, so its tamper probes never write to the input or anything
it links to. `--self-test`, part of `check-config.py`, checks that isolation
without a desktop or DMS. `--evidence /absolute/path.png` saves the rendered
fixture. Backend clipboard copy/paste and physical keyboard use are outside
these checks.

DMS 2.1.2 uses a separate reviewed patch for launcher rows, grid labels and image
tile captions. Generated search emphasis uses native styled text so Qt honors
line limits and ellipses; explicit `--markup-rows` dmenu HTML retains its rich
formatting. The older 2.0.0 slider and control-center patches are not applied
to changed 2.1 internals. The version, binary and each patched renderer must
match before the override launches. An upgrade to another version falls back
to built-in DMS until its source is reviewed again.

The 2.1.2 clipboard-history patch also covers the bar popout and centered history
modal, which share `ClipboardEntry.qml`. Image captions stay on one line, and
previews wrap long words and elide within the height the row has left below
the caption, so a single line keeps its full height even with dense spacing at
150% text scale. Newlines are flattened only for display; the stored preview,
accessible name and copy, paste, edit and pin actions retain the original data.
This renderer is included in the source and launch fingerprints.

```bash
python3 scripts/check-dms-clipboard-history-text.py --source-dir PRISTINE_DMS_2.1.2_UI
python3 scripts/check-dms-clipboard-history-text.py --source-dir PRISTINE_DMS_2.1.2_UI --unpatched  # reproduces the overflow
```

It uses the launcher check's private staging, launch-guard checks and isolated
headless desktop. The actual history rows are checked at 550/320 px, 115%/150%
text scale and normal/dense spacing (including dense at 150%) with multiline
text, unbroken URLs, image captions, literal markup and short text with
descenders, and the original previews must stay unchanged. `--evidence
/absolute/path.png` saves a synthetic rendering. The check does not exercise
the clipboard backend or touch the desktop clipboard.

As of 2026-11-13 the upstream history renderer is identical to the installed
2.1.2 renderer; the separate launcher fix has landed on upstream `master`.
The history patch can be submitted independently against
`quickshell/Modals/Clipboard/ClipboardEntry.qml` (apply with `patch -p1 -d
quickshell`). Upstream's [contribution policy](https://github.com/duxlabs-dev/dux-shell/blob/master/CONTRIBUTING.md#generative-ai)
allows AI-assisted code, requires disclosure and human review, and requires
human-written PR descriptions, issues and comments. The local config PR records
the fix and verification; an upstream submission still needs Mathis to review
the code and write its description.

Stage the reviewed change for the installed version (2.0.0 or 2.1.2) without
changing any running shell, then check the launch guard and launcher text:

```bash
python3 scripts/configure-dms-smooth-sliders.py --apply
python3 scripts/check-dms-smooth-sliders.py
python3 scripts/check-dms-launcher-text.py
python3 scripts/check-dms-clipboard-history-text.py  # DMS 2.1.2 only
```

On DMS 2.0.0 only, also check the slider patch. On other versions `--ui` stops
with a pointer to the launcher check, since they have no slider patch:

```bash
python3 scripts/check-dms-smooth-sliders.py --ui
```

`--ui` recovers pristine input by reversing the current patches on the stage
that `dms.path` points to. When the running shell still uses a stage made with
an earlier patch set (for example right after updating this repository), the
check stops and asks for pristine input instead. Pass an unmodified DMS 2.0.0
UI, such as the extracted `dms-qml.tar.gz` release asset:

```bash
python3 scripts/check-dms-smooth-sliders.py --ui --source-dir PRISTINE_DMS_2.0.0_UI
```

The helper reads the running shell's `dms.path` and copies its current extracted
UI into `~/.local/share/dms-ui-overrides`. It checks the exact reviewed DMS
version and the exact version-specific source hashes before applying all
patches. The manifest records the whole source tree's hash, combined patch hash,
all version-specific patched-file hashes, binary hash and
original source path. Reapplying while `dms.path` points at the override reads
the original source, so the patch is not applied twice. No system files or
extracted built-in files are changed. The patches live in
`shell-patches/guarded/` so the legacy DMS 1.5.x installer never applies them
without these checks.

The helper prints a supported `dms -c STAGED_UI run -d` command. For a durable
session launcher, use:

```bash
python3 scripts/configure-dms-smooth-sliders.py --launch
```

This launches the staged UI only when its DMS version and binary still match
and all patched files and the patch set are intact. After a package update, missing stage or
invalid manifest, it reports the reason and launches the built-in UI. Review
the new source and rerun setup before using the patch again. It never silently
keeps a previous DMS UI active after an update. Starting the launch command does
not stop an already running shell; activation requires a separate shell reload.

On DMS 2.0.0, the `--ui` check uses the real patched slider with a software-rendered offscreen
Qt window, isolated runtime and no display, desktop input or hardware service.
It checks an intermediate level, final settling, bounded rapid retargeting,
a held-key sequence with rendered progress between repeats, velocity kept
across a same-direction repeat, close retargets and reversals that stay between
the displayed position and the target on every frame, immediate model values,
no spurious user commits, and immediate drag and reduced-motion updates. It also checks repeat staging. No audio or real
brightness/volume change is involved.

For quick native feedback elsewhere, the preset can use 180 ms shell motion,
130 ms popouts, 160 ms modals, 140 ms notifications, standard motion and crisp
spring damping (`springBounce=0`). Those supported settings remain separate
from the shared slider patch.

Hyprland starts `dms/start-shell.py` from its linked configuration directory;
the wrapper calls this guarded launcher. Install `patch` from the Hyprland
package list when staging on a fresh machine.
