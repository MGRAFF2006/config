#!/usr/bin/env python3
"""Verify shared palette refresh preserves app preferences and custom colors."""

import importlib.util
import json
from pathlib import Path
import tempfile


def main():
    script = Path(__file__).with_name("configure-desktop-app-themes.py")
    spec = importlib.util.spec_from_file_location("desktop_app_themes", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix="app-theme-check-") as directory:
        root = Path(directory)
        module.CONFIG, module.DATA = root / "config", root / "data"
        module.STATE = root / "state"
        module.PALETTE = root / "palette.json"
        colors = {key: "#112233" for key in ("background", "surface", "surface_container", "surface_container_high", "on_surface", "primary", "on_primary")}
        module.PALETTE.write_text(json.dumps(colors))
        kde = module.CONFIG / "kdeglobals"
        kde.parent.mkdir(parents=True)
        kde.write_text("# Keep comment\n[General]\nfont=Large Accessible Font,14\nColorScheme=OldTheme\n\n[Colors:Window]\nBackgroundNormal=0,0,0\n\n[Icons]\nTheme=Papirus-Dark\n")
        scheme = module.DATA / "color-schemes/DankMatugen.colors"
        scheme.parent.mkdir(parents=True)
        scheme.write_text("[Colors:Window]\nBackgroundNormal=17,34,51\nForegroundNormal=255,255,255\n")
        vscode = module.CONFIG / "Code/User/settings.json"
        vscode.parent.mkdir(parents=True)
        vscode.write_text(json.dumps({"editor.fontSize": 20, "workbench.colorCustomizations": {"editorLineNumber.foreground": "#aabbcc"}}))
        vscode.chmod(0o640)
        module.refresh()
        result = json.loads(vscode.read_text())
        assert result["editor.fontSize"] == 20
        assert result["workbench.colorCustomizations"]["editorLineNumber.foreground"] == "#aabbcc"
        assert result["workbench.colorCustomizations"]["editor.background"] == "#112233"
        assert "BackgroundNormal=0,0,0" in kde.read_text()
        assert "font=Large Accessible Font,14" in kde.read_text()
        assert "# Keep comment" in kde.read_text() and "Theme=Papirus-Dark" in kde.read_text()
        assert vscode.stat().st_mode & 0o777 == 0o640
        before = kde.read_bytes(), vscode.read_bytes()
        module.refresh()
        assert before == (kde.read_bytes(), vscode.read_bytes())
        vscode.write_text('{\n// JSONC user preference\n"editor.fontSize": 20\n}')
        original = vscode.read_bytes()
        module.refresh()
        assert vscode.read_bytes() == original
        # Exercise apply against a stale smaller font and a larger accessible
        # choice. Native toolkit commands are the external boundary here.
        module.subprocess.run = lambda *args, **kwargs: None
        (module.DATA / "themes/adw-gtk3-dark").mkdir(parents=True)
        for version, font in [(3, "User Accessible 18"), (4, "Stale Default 10")]:
            gtk = module.CONFIG / f"gtk-{version}.0"
            gtk.mkdir()
            (gtk / "settings.ini").write_text(f"[Settings]\ngtk-font-name={font}\n")
            (gtk / "gtk.css").write_text('@import "colors.css";\n.custom { margin: 3px; }\n')
        module.apply()
        assert "gtk-font-name=User Accessible 18" in (module.CONFIG / "gtk-3.0/settings.ini").read_text()
        assert "gtk-font-name=Google Sans Flex, Medium 11" in (module.CONFIG / "gtk-4.0/settings.ini").read_text()
        css = (module.CONFIG / "gtk-4.0/gtk.css").read_text()
        assert '.custom { margin: 3px; }' in css and '"colors.css"' not in css
        module.apply()
        assert (module.CONFIG / "matugen/config.toml").read_text().count("[templates.desktop_shared_palette]") == 1
    print("PASS: shared palette updates editor (KDE owned by DMS), retains fonts/preferences/comments, permissions, idempotency, JSONC refusal")


if __name__ == "__main__":
    main()
