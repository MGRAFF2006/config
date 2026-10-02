#!/usr/bin/env python3
"""Connect desktop applications to the DMS theme and preferred app defaults."""

from __future__ import annotations

import configparser
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess


APP_HOME = Path(os.environ.get("CONFIG_LINK_HOME", Path.home()))
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME", APP_HOME / ".config"))
ZEN_ROOT = APP_HOME / ".zen"
ZEN_PROFILES = ZEN_ROOT / "profiles.ini"
DMS_ZEN_CSS = CONFIG_HOME / "DankMaterialShell/zen.css"
ZEN_USER_JS = CONFIG_HOME / "zen-browser/user.js"
ZEN_USER_CONTENT = CONFIG_HOME / "zen-browser/userContent.css"
KDE_GLOBALS = CONFIG_HOME / "kdeglobals"
DMS_COLOR_SCHEME = APP_HOME / ".local/share/color-schemes/DankMatugen.colors"
DMS_GTK_APPLIER = CONFIG_HOME / "DankMaterialShell/shell/scripts/gtk.sh"
FILE_MANAGER_DESKTOP = "org.gnome.Nautilus.desktop"


def default_zen_profile() -> Path | None:
    parser = configparser.ConfigParser()
    if not ZEN_PROFILES.exists():
        return None
    parser.read(ZEN_PROFILES)

    candidates: list[tuple[str, bool]] = []
    for section in parser.sections():
        if section.startswith("Install") and parser.has_option(section, "Default"):
            candidates.append((parser.get(section, "Default"), True))
    for section in parser.sections():
        if section.startswith("Profile") and parser.getboolean(section, "Default", fallback=False):
            candidates.append(
                (
                    parser.get(section, "Path", fallback=""),
                    parser.getboolean(section, "IsRelative", fallback=True),
                )
            )

    for value, relative in candidates:
        if not value:
            continue
        profile = ZEN_ROOT / value if relative else Path(value).expanduser()
        if profile.is_dir():
            return profile
    return None


def install_link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() and destination.resolve(strict=False) == source.resolve(strict=False):
        print(f"unchanged: {destination} -> {source}")
        return
    if destination.exists() or destination.is_symlink():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = destination.with_name(f"{destination.name}.pre-dms-{stamp}")
        destination.rename(backup)
        print(f"backed up: {destination} -> {backup}")
    destination.symlink_to(source)
    print(f"linked: {destination} -> {source}")


def run_if_available(command: str, *args: str) -> bool:
    executable = shutil.which(command)
    if not executable:
        return False
    subprocess.run([executable, *args], check=True)
    return True


def configure_zen() -> None:
    profile = default_zen_profile()
    if not profile:
        print("skipped Zen: no default profile found")
        return
    if not ZEN_USER_JS.exists():
        raise SystemExit(f"Missing managed Zen preferences: {ZEN_USER_JS}")
    if not DMS_ZEN_CSS.exists():
        print(f"warning: DMS has not generated {DMS_ZEN_CSS} yet; the link will become active when it does")
    install_link(DMS_ZEN_CSS, profile / "chrome/userChrome.css")
    install_link(ZEN_USER_CONTENT, profile / "chrome/userContent.css")
    install_link(ZEN_USER_JS, profile / "user.js")


def configure_desktop_defaults() -> None:
    # DMS reads the initialized settings when it starts; setup also works without
    # an active shell/IPC endpoint on a fresh machine.
    for mime_type in ("inode/directory", "x-scheme-handler/file"):
        run_if_available("xdg-mime", "default", FILE_MANAGER_DESKTOP, mime_type)

    if DMS_GTK_APPLIER.exists():
        subprocess.run(
            [str(DMS_GTK_APPLIER), str(CONFIG_HOME), "false", str(DMS_GTK_APPLIER.parents[1])],
            check=True,
        )

    if DMS_COLOR_SCHEME.exists():
        run_if_available(
            "kwriteconfig6",
            "--file",
            str(KDE_GLOBALS),
            "--group",
            "General",
            "--key",
            "ColorScheme",
            "--notify",
            "DankMatugen",
        )
    run_if_available(
        "kwriteconfig6",
        "--file",
        str(KDE_GLOBALS),
        "--group",
        "General",
        "--key",
        "BrowserApplication",
        "--notify",
        "zen.desktop",
    )
    print("defaults: Nautilus for folders and Zen for web links; start DMS to generate application colors")


def main() -> int:
    configure_zen()
    configure_desktop_defaults()
    print("Restart Zen once to load its managed theme and performance preferences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
