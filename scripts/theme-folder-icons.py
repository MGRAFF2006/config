#!/usr/bin/env python3
"""Generate small Papirus folder overlays from the current wallpaper palette."""

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SIZES = (16, 22, 24, 32, 48, 64)
NAMED_COLORS = "black bluegrey brown carmine cyan green grey indigo magenta nordic orange palebrown paleorange pink red teal violet white yellow".split()
STANDARD = {"folder", "folder-home", "user-home", "user-desktop", "desktop"}


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == content:
        return
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def recolor(svg, primary, on_primary):
    rgb = tuple(int(primary[index:index + 2], 16) for index in (1, 3, 5))
    rear = "#" + "".join(f"{round(channel * 0.72):02x}" for channel in rgb)
    replacements = {"#5294e2": primary, "#4877b1": rear, "#1d344f": on_primary}
    for source, destination in replacements.items():
        svg = re.sub(re.escape(source), destination, svg, flags=re.IGNORECASE)
    # At small sizes Papirus uses toolkit-recolored monochrome paths. Make the
    # folder accent explicit while retaining the original shape and opacity.
    svg = svg.replace("fill:currentColor", "fill:" + primary)
    return svg


def generate(palette, destination, system=Path("/usr/share/icons")):
    primary, on_primary = palette["primary"], palette["on_primary"]
    if not all(isinstance(color, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", color) for color in (primary, on_primary)):
        raise ValueError("Folder colors must be six-digit hexadecimal colors")
    if not (system / "Papirus/index.theme").is_file():
        raise FileNotFoundError("Install papirus-icon-theme before generating the overlay")
    count = 0
    for base in ("Papirus", "Papirus-Dark"):
        theme = destination / ("DMS-" + base)
        directories = []
        for size in SIZES:
            relative = f"{size}x{size}/places"
            source_dir = system / base / relative
            if not source_dir.is_dir():
                continue
            names = sorted({*source_dir.glob("folder*.svg"), *(source_dir / (name + ".svg") for name in STANDARD)})
            for source in names:
                if not source.is_file():
                    continue
                stem = source.stem
                if any(stem == "folder-" + color or stem.startswith("folder-" + color + "-") for color in NAMED_COLORS):
                    continue
                svg = source.read_text()
                # Do not reinterpret other explicit folder colors or graphics.
                if "#5294e2" not in svg.lower() and "fill:currentColor" not in svg and stem not in STANDARD:
                    continue
                write(theme / relative / source.name, recolor(svg, primary, on_primary))
                count += 1
            directories.append((relative, size))
        index = f"[Icon Theme]\nName=DMS-{base}\nComment=Wallpaper-colored Papirus folders\nInherits={base}\nDirectories="
        index += ",".join(path for path, _ in directories) + "\n"
        for path, size in directories:
            index += f"\n[{path}]\nSize={size}\nContext=Places\nType=Fixed\n"
        write(theme / "index.theme", index)
        notice = "Folder artwork: Papirus Development Team, GPL-3.0.\nhttps://github.com/PapirusDevelopmentTeam/papirus-icon-theme\n"
        notice += f"Locally recolored by theme-folder-icons.py on {date.today().isoformat()}; geometry and glyphs retained.\n"
        write(theme / "NOTICE", notice)
        license_path = Path("/usr/share/licenses/spdx/GPL-3.0-only.txt")
        if license_path.exists():
            write(theme / "COPYING", license_path.read_text())
        if shutil.which("gtk-update-icon-cache"):
            subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(theme)], check=True, capture_output=True, text=True)
    return count


def main():
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--palette", type=Path, default=config / "desktop-theme/palette.json")
    args = parser.parse_args()
    count = generate(json.loads(args.palette.read_text()), data / "icons")
    print(f"Updated {count} Papirus folder/place icons across DMS-Papirus and DMS-Papirus-Dark.")


if __name__ == "__main__":
    main()
