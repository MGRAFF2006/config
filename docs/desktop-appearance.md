# Electric glass desktop

The expressive preset uses blue/cyan/violet window borders, acrylic blur,
subtle inner glow, spring window motion, rounded corners and a floating glass
bar. General application opacity stays unchanged; selected tool windows have
translucent surfaces and fullscreen compositor opacity is restored to 100%.
DMS keeps the existing widgets,
shortcuts, screen layout and plugins. Animated blur simulations are not enabled.

Deploy the Hyprland component with the existing setup flow, then preview/apply:

```bash
bash scripts/link-home.sh laptop --dry-run
bash scripts/link-home.sh laptop
python3 scripts/configure-desktop-appearance.py
python3 scripts/configure-desktop-appearance.py --apply
```

Use `desktop` instead of `laptop` on the other workstation. The helper prints
a backup directory and exact restore command before writing anything. Restore
returns the complete previous DMS settings and user layout; it also backs up
the current state. Neither applying nor restoring changes the wallpaper.
Theme paths follow the checkout used to apply the preset; keep that checkout.

DMS settings remain machine-local. `dms/expressive.lua` is loaded after the
generated layout and colors through `layout-user.lua`; DMS regeneration does
not erase it. For ordinary frosted blur, set `variant = "kawase"` in that file.
The acrylic/glow block is guarded for versions without those options. The
preset targets Hyprland's Lua configuration API and DMS 2.0.
