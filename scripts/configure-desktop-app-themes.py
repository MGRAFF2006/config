#!/usr/bin/env python3
"""Connect GTK, KDE, Neovim and VS Code to DMS's wallpaper palette."""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
STATE = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
DATA = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
PALETTE = CONFIG / "desktop-theme/palette.json"


def write(path, text):
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    old = path.stat() if path.exists() else None
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        if old:
            os.fchmod(fd, old.st_mode & 0o777)
            os.fchown(fd, -1, old.st_gid)
        with os.fdopen(fd, "w") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def refresh():
    colors = json.loads(PALETTE.read_text())
    if not all(re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in colors.values()):
        raise ValueError("Invalid generated desktop palette")
    subprocess.run(["python3", str(ROOT / "scripts/theme-folder-icons.py"), "--palette", str(PALETTE)], env=dict(os.environ, XDG_DATA_HOME=str(DATA)), check=True)
    vscode = CONFIG / "Code/User/settings.json"
    if vscode.exists():
        try:
            settings = json.loads(vscode.read_text())
        except json.JSONDecodeError:
            print("VS Code settings use JSONC: left unchanged; select the DMS theme manually.")
        else:
            owned = {
                "editor.background": colors["background"], "editor.foreground": colors["on_surface"],
                "sideBar.background": colors["surface_container"], "sideBar.foreground": colors["on_surface"],
                "activityBar.background": colors["surface"], "activityBar.foreground": colors["primary"],
                "statusBar.background": colors["surface_container"], "statusBar.foreground": colors["on_surface"],
                "titleBar.activeBackground": colors["surface"], "titleBar.activeForeground": colors["on_surface"],
                "tab.activeBackground": colors["background"], "tab.activeForeground": colors["primary"],
                "tab.inactiveBackground": colors["surface_container"],
                "panel.background": colors["background"], "focusBorder": colors["primary"],
                "button.background": colors["primary"], "button.foreground": colors["on_primary"],
                "input.background": colors["surface_container_high"],
            }
            settings.setdefault("workbench.colorCustomizations", {}).update(owned)
            write(vscode, json.dumps(settings, indent=4) + "\n")


def apply():
    # Keep existing accessibility choices across toolkit setup. The managed
    # baseline is a minimum when a stale system default is smaller.
    fonts = {}
    for version in (3, 4):
        ini = CONFIG / f"gtk-{version}.0/settings.ini"
        source = ROOT / f"home/.config/gtk-{version}.0/settings.ini"
        existing = re.search(r"(?m)^gtk-font-name=(.*)$", ini.read_text() if ini.exists() else "")
        managed = re.search(r"(?m)^gtk-font-name=(.*)$", source.read_text() if source.exists() else "")
        fonts[version] = existing[1] if existing else (managed[1] if managed else "")
        if existing and managed:
            current_size = re.search(r"([\d.]+)\s*$", existing[1])
            minimum_size = re.search(r"([\d.]+)\s*$", managed[1])
            if current_size and minimum_size and float(current_size[1]) < float(minimum_size[1]):
                fonts[version] = managed[1]
    targets = [CONFIG / "matugen/config.toml", CONFIG / "kdeglobals", CONFIG / "Code/User/settings.json"]
    targets += [CONFIG / f"gtk-{version}.0/gtk.css" for version in (3, 4)]
    targets += [CONFIG / f"gtk-{version}.0/settings.ini" for version in (3, 4)]
    backup_root = STATE / "config/app-theme-backups"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y-%m-%d_%H-%M-%S-"), dir=backup_root))
    for path in targets:
        if path.exists():
            destination = backup / path.relative_to(CONFIG)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    print(f"Backup: {backup}", flush=True)
    template = ROOT / "home/.config/matugen/templates/desktop-palette.json"
    command = shlex.join(["python3", str(Path(__file__).resolve()), "--refresh"])
    block = '\n# BEGIN shared desktop palette\n[templates.desktop_shared_palette]\n'
    block += f"input_path = {json.dumps(str(template))}\noutput_path = {json.dumps(str(PALETTE))}\npost_hook = {json.dumps(command)}\n"
    block += "# END shared desktop palette\n"
    config = CONFIG / "matugen/config.toml"
    content = config.read_text() if config.exists() else "[config]\n"
    tomllib.loads(content)
    content = re.sub(r"(?ms)\n# BEGIN shared desktop palette\n.*?# END shared desktop palette\n", "", content)
    write(config, content + block)
    for version in (3, 4):
        css = CONFIG / f"gtk-{version}.0/gtk.css"
        content = css.read_text() if css.exists() else ""
        content = re.sub(r"@import\s+(?:url\()?['\"]colors\.css['\"]\)?\s*;", "", content)
        if "dank-colors.css" not in content:
            content = '@import url("dank-colors.css");\n' + content
        write(css, content)
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    shell_path = runtime / "dms.path"
    if shell_path.exists():
        gtk = Path(shell_path.read_text().strip()) / "scripts/gtk.sh"
        if gtk.exists():
            subprocess.run(["bash", str(gtk), str(CONFIG), "apply", "false"], check=True)
    if (DATA / "themes/adw-gtk3-dark").exists() or Path("/usr/share/themes/adw-gtk3-dark").exists():
        for version in (3, 4):
            ini = CONFIG / f"gtk-{version}.0/settings.ini"
            content = ini.read_text() if ini.exists() else "[Settings]\n"
            if re.search(r"(?m)^gtk-theme-name=", content):
                content = re.sub(r"(?m)^gtk-theme-name=.*$", "gtk-theme-name=adw-gtk3-dark", content)
            else:
                content = content.replace("[Settings]\n", "[Settings]\ngtk-theme-name=adw-gtk3-dark\n", 1)
            if fonts[version]:
                if re.search(r"(?m)^gtk-font-name=", content):
                    content = re.sub(r"(?m)^gtk-font-name=.*$", "gtk-font-name=" + fonts[version], content)
                else:
                    content += "\ngtk-font-name=" + fonts[version] + "\n"
            write(ini, content)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", "adw-gtk3-dark"], check=True)
        if fonts[3]:
            subprocess.run(["gsettings", "set", "org.gnome.desktop.interface", "font-name", fonts[3]], check=True)
    if PALETTE.exists():
        refresh()
    print("Installed the palette hook. Change wallpaper/theme in DMS to generate it.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    if args.apply:
        apply()
    else:
        refresh()


if __name__ == "__main__":
    main()
