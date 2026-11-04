# Readable glass with wallpaper colors

This preset keeps 2 px gaps and 2 px window corners while giving the shell
large text and controls. DMS uses a 115% font scale, larger bar text/icons,
and a fixed 4 px radius for shell controls. Window, workspace and panel transitions finish
quickly with tiny scale/position changes, short fades and no spring overshoot.
Workspace transitions combine a short slide with a fade, so outgoing windows
fade away smoothly when the next workspace is empty.
Hover/press feedback remains enabled. Acrylic blur, shadows and a narrow inner
glow add depth without continuous animation. Volume/brightness level smoothing
is provided separately through a user-local DMS slider override.

DMS's dynamic theme derives the shell and generated app colors from the
wallpaper. The compositor keeps generated colors instead of overriding them
with a static gradient. GTK, Qt/KDE, Alacritty and Zen templates are enabled.
The wallpaper uses DMS's built-in geometric Material composition, preset
`garden`, with a cool accent chosen in DMS; there is no generated illustration.
Choose another image or Material seed through DMS to update the palette.

Deploy through the existing setup flow, then preview/apply the shell preset:

```bash
bash scripts/link-home.sh laptop --dry-run
bash scripts/link-home.sh laptop
python3 scripts/configure-desktop-appearance.py
python3 scripts/configure-desktop-appearance.py --apply
python3 scripts/configure-desktop-app-themes.py --apply
dms ipc call wallpaper clear
```

Use `desktop` instead of `laptop` on the other workstation. Review the linker
preview: it also deploys the rest of that machine's configuration. Existing
widgets, plugins, workspace logic, terminal fonts and screen layout are retained.
The preset does not itself change application font settings.

The helper prints a backup directory and exact restore command before writing.
Restore returns the complete previous DMS settings and user layout, and also
backs up the current state. Applying/restoring does not change the wallpaper:
choose it separately through DMS. The previous wallpaper file remains available.
Settings and their backups remain machine-local.

`dms/expressive.lua` loads after generated layout/colors through `layout-user.lua`.
DMS regeneration does not erase it. For plain frosted blur, change
`variant = "acrylic"` to `variant = "kawase"`. The new blur/glow block is guarded
for versions without those options; the preset targets Hyprland's Lua API
and DMS 2.0. The built-in Neovim template is disabled because it requires
base46; use the repository's app-theme integration instead.

The cross-toolkit approach follows [dwm-titus's shared application palette](https://dwm.christitus.com/theming.html)
and [DMS's native application theme integration](https://duxlabs.dev/docs/dms/application-themes).

In DMS Wallpaper settings, select a Material preset and choose a
cool accent color. `wallpaper clear` restores the saved/default Material layout.
