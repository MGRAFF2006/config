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
progress. The `smooth-slider-level.patch` uses Qt’s velocity-preserving
`SmoothedAnimation` on a separate visual ratio, with a 120 ms tracking duration.
Held-key repeats retarget the running movement without restarting the easing on
every step. The real value, adjustment signal and hardware update remain immediate. Pointer dragging, reduced motion and disabled animations
bypass the transition.

Launcher results use single-line native styled-text elision for both the title
and subtitle, preserving search emphasis. Display-only newline normalization
keeps multiline clipboard entries within their rows; the full name, clipboard
payload and accessible label remain unchanged. The guarded patch set also
fingerprints `LauncherRow.qml` before applying this correction.

DMS 2.1.2 uses a separate reviewed patch for launcher rows, grid labels and image
tile captions. Generated search emphasis uses native styled text so Qt honors
line limits and ellipses; explicit dmenu HTML retains its rich formatting. The
older 2.0.0 slider and control-center patches are not applied to changed 2.1
internals. The version, binary and each patched renderer must match before the
override launches. An upgrade to another version falls back to built-in DMS
until its source is reviewed again.

The 2.1.2 clipboard-history patch also covers the bar popout and centered history
modal, which share `ClipboardEntry.qml`. Image captions stay on one line, and
previews wrap long words and elide within the row's remaining height. Newlines
are flattened only for display; the stored preview, accessible name and copy,
paste, edit and pin actions retain the original data. This renderer is included
in the source and launch fingerprints.

Run `agent-desktop run python3 scripts/check-dms-clipboard-history-text.py
--source-dir /path/to/pristine/dms-ui` in the private agent desktop. The actual
history rows are checked at 550/320 px, 115%/150% text scale, and normal/dense
spacing with multiline text, unbroken URLs, image captions, literal markup and
short text. `--unpatched` reproduces the overflow; `--evidence /absolute/path.png`
saves a synthetic rendering. The check does not exercise the clipboard backend
or change the human clipboard.

As of 2026-11-13 the upstream history renderer is identical to the installed
2.1.2 renderer; the separate launcher fix has landed on upstream `master`.
The history patch can be submitted independently against
`quickshell/Modals/Clipboard/ClipboardEntry.qml` (apply with `patch -p1 -d
quickshell`). Upstream's [contribution policy](https://github.com/duxlabs-dev/dux-shell/blob/master/CONTRIBUTING.md#generative-ai)
allows AI-assisted code, requires disclosure and human review, and requires
human-written PR descriptions, issues and comments. The local config PR records
the fix and verification; an upstream submission still needs Mathis to review
the code and write its description.

Check actual launcher components with synthetic clipboard data in the separate
agent desktop (no physical desktop input or clipboard access):

```bash
agent-desktop start
agent-desktop run python3 "$PWD/scripts/check-dms-launcher-text.py" --source-dir /path/to/pristine/dms-ui
```

The helper logs to the agent desktop's `apps.log`. `--unpatched` reproduces the
original failure; `--evidence /absolute/path.png` saves the patched fixture.
Coverage includes grid widths 180/120 px, row widths 620/320 px, multiline and
highlighted entries, long subtitles, image captions, ordinary short app labels,
115% text scale, unchanged payloads, explicit dmenu HTML, repeat staging and
renderer-tamper/version fallback. The fixture exercises the actual rendering
components; backend clipboard copy/paste and physical keyboard use are separate
from these checks.

Stage the reviewed change without changing any running shell:

```bash
python3 scripts/configure-dms-smooth-sliders.py --apply
python3 scripts/check-dms-smooth-sliders.py
python3 scripts/check-dms-smooth-sliders.py --ui
```

The helper reads the running shell's `dms.path` and copies its current extracted
UI into `~/.local/share/dms-ui-overrides`. It checks the exact reviewed DMS
version and the exact version-specific source hashes before applying all
patches. The manifest records the whole source tree's hash, combined patch hash,
all version-specific patched-file hashes, binary hash and
original source path. Reapplying while `dms.path` points at the override reads
the original source, so the patch is not applied twice. No system files or
extracted built-in files are changed.

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
a held-key sequence with rendered progress between repeats, immediate model values, no spurious user commits, and immediate drag
and reduced-motion updates. It also checks repeat staging. No audio or real
brightness/volume change is involved.

For quick native feedback elsewhere, the preset can use 180 ms shell motion,
130 ms popouts, 160 ms modals, 140 ms notifications, standard motion and crisp
spring damping (`springBounce=0`). Those supported settings remain separate
from the shared slider patch.

Hyprland starts `dms/start-shell.py` from its linked configuration directory;
the wrapper calls this guarded launcher. Install `patch` from the Hyprland
package list when staging on a fresh machine.
