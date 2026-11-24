#!/usr/bin/env python3
"""Connect desktop applications to the DMS theme and preferred app defaults."""

from __future__ import annotations

import configparser
from datetime import datetime
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


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
ONLYOFFICE_SETTINGS = CONFIG_HOME / "onlyoffice/DesktopEditors.conf"
UTF8_BOM = b"\xef\xbb\xbf"


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


def qt_ini_lines(data: bytes, pos: int = 0):
    """Yield QSettings' logical INI lines as (start, end, equals) byte offsets.

    Mirrors Qt's reader: leading whitespace and blank lines are skipped, `;`
    starts a comment, and quoted values or backslash escapes continue a line.
    """
    size = len(data)
    while True:
        start = pos
        while start < size and data[start] in b" \t\r\n":
            start += 1
        i, equals, quoted = start, -1, False
        while i < size:
            char = data[i]
            i += 1
            if char == ord("="):
                if not quoted and equals == -1:
                    equals = i - 1
            elif char in b"\r\n":
                if i == start + 1:
                    start += 1
                elif not quoted:
                    i -= 1
                    break
            elif char == ord("\\"):
                if i < size:
                    escaped = data[i]
                    i += 1
                    if i < size and {escaped, data[i]} == {ord("\r"), ord("\n")}:
                        i += 1
            elif char == ord('"'):
                quoted = not quoted
            elif char == ord(";"):
                if i == start + 1:
                    while i < size and data[i] not in b"\r\n":
                        i += 1
                    while i < size and data[i] in b" \t\r\n":
                        i += 1
                    start = i
                elif not quoted:
                    i -= 1
                    break
        pos = i
        if i <= start:
            return
        yield start, i, equals


def with_system_titlebar(data: bytes) -> bytes:
    """Set the effective `General/titlebar` to `system`, leaving other bytes alone."""
    newline = b"\r\n" if b"\r\n" in data else b"\n"
    body = len(UTF8_BOM) if data.startswith(UTF8_BOM) else 0
    in_general = True  # Qt reads keys before any group header as General.
    general_header = None
    titlebars = []
    for start, end, equals in qt_ini_lines(data, body):
        line = data[start:end]
        if line.startswith(b"["):
            close = line.find(b"]")
            name = line[1:close] if close != -1 else line[1:]
            in_general = name.strip().lower() == b"general"
            if in_general and general_header is None:
                general_header = end
        elif in_general and equals != -1 and data[start:equals].rstrip(b" \t") == b"titlebar":
            titlebars.append((start, end))

    entry = b"titlebar=system"
    if titlebars:
        # Repeated General groups and keys are merged by Qt; the last one wins,
        # so replace each to keep the file unambiguous.
        for start, end in reversed(titlebars):
            data = data[:start] + entry + data[end:]
        return data
    if general_header is not None:
        line_end = general_header  # skip a trailing comment on the header line
        while line_end < len(data) and data[line_end] not in b"\r\n":
            line_end += 1
        if line_end == len(data):
            return data + newline + entry + newline
        line_end += 2 if data[line_end : line_end + 2] == b"\r\n" else 1
        return data[:line_end] + entry + newline + data[line_end:]
    # Qt writes General first; prepending also avoids an unterminated trailing value.
    group = b"[General]" + newline + entry + newline
    rest = data[body:]
    return data[:body] + group + (newline + rest if rest else b"")


def onlyoffice_running() -> bool:
    for comm in Path("/proc").glob("[0-9]*/comm"):
        try:
            if comm.read_text().strip() == "DesktopEditors":
                return True
        except OSError:
            continue
    return False


def replace_if_unchanged(path: Path, original: bytes | None, updated: bytes) -> bool:
    """Atomically write `updated` unless another writer changed `path` meanwhile."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if original is None:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    else:
        mode = stat.S_IMODE(path.stat().st_mode)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        current = path.read_bytes() if path.exists() else None
        if current != original:
            os.unlink(temporary)
            return False
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
    return True


def configure_onlyoffice() -> None:
    if not shutil.which("onlyoffice-desktopeditors"):
        return
    # The custom frame reserves invisible shadow padding inside Hyprland tiles.
    # Edit just this key: KDE's INI writer rewrites QSettings' geometry escapes.
    rerun = "save documents, close OnlyOffice and rerun scripts/configure-dms-app-integration.py"
    if onlyoffice_running():
        # OnlyOffice writes its in-memory settings back when it exits.
        print(f"skipped OnlyOffice: it is running; {rerun} to use the system window frame")
        return
    settings = Path(os.path.realpath(ONLYOFFICE_SETTINGS))
    original = settings.read_bytes() if settings.exists() else None
    updated = with_system_titlebar(original or b"")
    if updated == original:
        print("unchanged: OnlyOffice uses the system window frame")
    elif replace_if_unchanged(settings, original, updated):
        print("OnlyOffice: system window frame enabled for its next start")
    else:
        print(f"skipped OnlyOffice: {settings} changed while updating; {rerun}")


def main() -> int:
    configure_zen()
    configure_desktop_defaults()
    configure_onlyoffice()
    print("Restart Zen once to load its managed theme and performance preferences.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
