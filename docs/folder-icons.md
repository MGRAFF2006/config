# Wallpaper-colored folder icons

`python3 scripts/theme-folder-icons.py` reads the generated
`~/.config/desktop-theme/palette.json` and builds two small icon overlays:
`DMS-Papirus-Dark` inherits `Papirus-Dark`; `DMS-Papirus` inherits `Papirus`.
`--palette PATH` supports a different generated palette for isolated checks.

Only folder/place artwork is generated, at 16, 22, 24, 32, 48 and 64 px.
Generic folders, open folders and the standard home, documents, downloads,
music, pictures, videos and desktop icons follow the palette. SVG geometry,
paper neutrals, highlight and shadow opacity remain intact. The front folder
uses the exact primary accent, its rear flap uses a darker shade, and its glyph
uses the corresponding readable foreground. Explicit red/green/etc. folders
keep their inherited semantic colors. Application logos remain inherited.

The installed `papirus-icon-theme` package supplies the source SVGs. The
generated files live under `XDG_DATA_HOME/icons` (normally
`~/.local/share/icons`) and the helper refreshes their icon caches. It does not
modify system icons, install a service, or copy the full icon theme. The shared
Matugen hook should call the helper once per generated palette. Select the two
overlay names as DMS's dark/light icon themes.

Papirus artwork is from the [Papirus Development Team](https://github.com/PapirusDevelopmentTeam/papirus-icon-theme)
under [GPL-3.0](https://github.com/PapirusDevelopmentTeam/papirus-icon-theme/blob/master/LICENSE).
Each local overlay carries an attribution/change notice and, when available,
a copy of the installed SPDX GPL-3.0 license. No derivative SVGs are committed
to this repository.

Run `python3 scripts/check-folder-icons.py` to check recoloring, glyph/shadow
preservation, alias resolution, all six sizes and application-icon inheritance.
To undo, select `Papirus-Dark`/`Papirus` again and remove the two local overlays.
