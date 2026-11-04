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

Stage the reviewed change without changing any running shell:

```bash
python3 scripts/configure-dms-smooth-sliders.py --apply
python3 scripts/check-dms-smooth-sliders.py
python3 scripts/check-dms-smooth-sliders.py --ui
```

The helper reads the running shell's `dms.path` and copies its current extracted
UI into `~/.local/share/dms-ui-overrides`. It checks the exact reviewed DMS
version and the exact slider/control-center source hashes before applying both
patches. The manifest records the whole source tree's hash, combined patch hash,
all three patched-file hashes, binary hash and
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

The `--ui` check uses the real patched slider with a software-rendered offscreen
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
