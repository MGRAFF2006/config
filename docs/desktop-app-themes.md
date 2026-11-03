# One wallpaper palette across applications

The desktop follows DMS's dynamic wallpaper palette. The approach follows
[dwm-titus's shared desktop palette](https://dwm.christitus.com/theming.html):
one set of surfaces, text and accents reaches each toolkit rather than choosing
unrelated application themes.

Enable DMS's own GTK, KColorScheme, Alacritty and Zen templates, plus **Run DMS
templates** and **Run user templates**. Keep the built-in Neovim template off:
it requires a different base46 setup. The existing Kickstart configuration uses
the small `custom.dms-theme` module instead, retaining its syntax highlights.

Install the Hyprland component's `adw-gtk-theme`, `plasma-integration` and
`plasma5-integration` packages. The session uses `QT_QPA_PLATFORMTHEME=kde` for
both Qt generations. Then run:

```bash
python3 scripts/configure-desktop-app-themes.py --apply
```

The helper prints a private backup directory before modifying existing files.
It installs DMS's native GTK integration, removes the obsolete `colors.css`
import that overrode the generated GTK palette, and adds one user Matugen
template. It changes no application defaults or credentials. GTK font choices
larger than the managed baseline are retained; stale smaller defaults are
raised to the managed 11 pt font so setup cannot reduce configured text size.
Applying again replaces its own marked template block and preserves unrelated
Matugen configuration. Apply the dark desktop preset first; the initial GTK
selection is `adw-gtk3-dark` and DMS manages subsequent light/dark changes.

On every wallpaper/theme generation, Matugen writes
`~/.config/desktop-theme/palette.json` and runs the helper's `--refresh` hook.
VS Code's backgrounds, text and UI accents update from this palette without
replacing its font, syntax, extension or other preferences. Existing custom
color keys outside the desktop surfaces are retained. Settings containing JSONC
comments are reported and left untouched rather than being rewritten as JSON.
Neovim reads the same palette on startup and focus return. No extra background
service or watcher runs.

DMS generates and applies KDE's native KColorScheme after all templates; the
hook does not duplicate this operation. Alacritty already imports
`dank-theme.toml` after its fallback palette and reloads live. Zen's existing
`chrome/userChrome.css` link reads DMS's `zen.css` after a browser restart.

Existing GTK applications can cache their stylesheet; reopen them if necessary.
Qt applications opened before the KDE platform-theme setting need reopening.
Web content keeps its own site colors. Flatpak sandboxes, games and applications
that draw their own UI (including T3 Code and the Craft suite) can require their
own appearance settings; a native palette cannot force those applications to
adopt unsupported custom colors. This setup does not inject code into them.

Verification includes both native Qt5 and Qt6 palette queries against the same
generated background, text and accent values; Neovim's actual `Normal`
highlight; and a red-to-blue Matugen generation check that updates VS Code while
retaining its font setting. Run the preservation checks with:

```bash
python3 scripts/check-desktop-app-themes.py
```

To undo the shared hook, remove the marked `shared desktop palette` block from
`~/.config/matugen/config.toml`, restore the saved app configuration files from
the printed backup, and remove the `custom.dms-theme` setup line from Neovim.
The generated `desktop-theme/palette.json` can then be removed. DMS's native
GTK/Qt theming remains selectable through its own application-theme settings.
