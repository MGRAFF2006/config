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
payload and accessible label remain unchanged. The guarded patch set also
fingerprints `LauncherRow.qml` before applying this correction.

Stage the reviewed change without changing any running shell:

```bash
python3 scripts/configure-dms-smooth-sliders.py --apply
python3 scripts/check-dms-smooth-sliders.py
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
version and the exact slider/control-center source hashes before applying all
patches. The manifest records the whole source tree's hash, combined patch hash,
all four patched-file hashes, binary hash and
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

The `--ui` check uses the real patched slider with a software-rendered offscreen
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
