#!/usr/bin/env python3
"""Verify the OnlyOffice frame setting edits only Qt's effective General key."""

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile


CASES = [
    # Valid Qt whitespace around '=' and another group's key of the same name.
    (b"[General]\ntitlebar = custom\n[other]\ntitlebar=keep\n",
     b"[General]\ntitlebar=system\n[other]\ntitlebar=keep\n"),
    # An indented header still starts a group; its key must stay untouched.
    (b"[General]\nfoo=1\n  [other]\ntitlebar=keep\n",
     b"[General]\ntitlebar=system\nfoo=1\n  [other]\ntitlebar=keep\n"),
    # Qt merges repeated General groups (case-insensitive) and the last key wins.
    (b"[General]\ntitlebar=custom\n[other]\na=1\n[general]\ntitlebar=custom\n",
     b"[General]\ntitlebar=system\n[other]\na=1\n[general]\ntitlebar=system\n"),
    # Header-like lines inside a quoted multiline value are not groups.
    (b'[General]\nnote="x\n[other]\ntitlebar=custom"\ntitlebar=custom\n',
     b'[General]\nnote="x\n[other]\ntitlebar=custom"\ntitlebar=system\n'),
    (b'[other]\nnote="x\n[General]\ny"\ntitlebar=keep\n',
     b'[General]\ntitlebar=system\n\n[other]\nnote="x\n[General]\ny"\ntitlebar=keep\n'),
    # Keys before any header belong to General.
    (b"titlebar=custom\n[other]\na=1\n",
     b"titlebar=system\n[other]\na=1\n"),
    # Comments are not keys.
    (b"[General]\n;titlebar=custom\n",
     b"[General]\ntitlebar=system\n;titlebar=custom\n"),
    # CRLF is preserved for existing and inserted lines.
    (b"[General]\r\ntitlebar=custom\r\n[other]\r\nbar=2\r\n",
     b"[General]\r\ntitlebar=system\r\n[other]\r\nbar=2\r\n"),
    (b"[General]\r\nfoo=1\r\n[other]\r\nbar=2\r\n",
     b"[General]\r\ntitlebar=system\r\nfoo=1\r\n[other]\r\nbar=2\r\n"),
    # A header comment stays on its line; CR-only line ends do not move the key.
    (b"[General] ; app settings\n[other]\na=1\n",
     b"[General] ; app settings\ntitlebar=system\n[other]\na=1\n"),
    (b"[General]\rfoo=1\r[other]\ra=1",
     b"[General]\rtitlebar=system\nfoo=1\r[other]\ra=1"),
    # Header-only file without a trailing newline.
    (b"[General]", b"[General]\ntitlebar=system\n"),
    (b"", b"[General]\ntitlebar=system\n"),
    # Escaped geometry in another group stays byte-for-byte identical.
    (b"[General]\ntitlebar=custom\n\n[MainWindow]\ngeometry=@ByteArray(\\x1\\xd9\\xd0\\xcb)\n",
     b"[General]\ntitlebar=system\n\n[MainWindow]\ngeometry=@ByteArray(\\x1\\xd9\\xd0\\xcb)\n"),
]


def load():
    script = Path(__file__).with_name("configure-dms-app-integration.py")
    spec = importlib.util.spec_from_file_location("dms_app_integration", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.shutil.which = lambda name: f"/stub/{name}"
    return module


def run(module):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        module.configure_onlyoffice()
    return output.getvalue()


def main():
    module = load()
    assert isinstance(module.onlyoffice_running(), bool)
    module.onlyoffice_running = lambda: False
    for original, expected in CASES:
        updated = module.with_system_titlebar(original)
        assert updated == expected, (original, updated)
        assert module.with_system_titlebar(updated) == updated, updated

    real_fsync = module.os.fsync
    with tempfile.TemporaryDirectory(prefix="onlyoffice-titlebar-check-") as directory:
        settings = Path(directory) / "onlyoffice/DesktopEditors.conf"
        module.ONLYOFFICE_SETTINGS = settings

        assert "enabled" in run(module)
        assert settings.read_bytes() == b"[General]\ntitlebar=system\n"

        original = b"[General]\r\ntitlebar = custom\r\n[other]\r\nappdata=old\r\n"
        settings.write_bytes(original)
        settings.chmod(0o640)
        run(module)
        assert settings.read_bytes() == original.replace(b"titlebar = custom", b"titlebar=system")
        assert settings.stat().st_mode & 0o777 == 0o640
        stable = settings.read_bytes()
        assert "unchanged" in run(module) and settings.read_bytes() == stable

        # A running OnlyOffice rewrites its settings on exit, so leave the file alone.
        settings.write_bytes(original)
        module.onlyoffice_running = lambda: True
        assert "close OnlyOffice" in run(module) and settings.read_bytes() == original
        module.onlyoffice_running = lambda: False

        def fail(*args):
            raise OSError("injected write failure")

        module.os.fsync = fail
        try:
            run(module)
        except OSError:
            pass
        else:
            raise AssertionError("injected write failure was not raised")
        finally:
            module.os.fsync = real_fsync
        assert settings.read_bytes() == original

        concurrent = original + b"saved=elsewhere\r\n"

        def save_elsewhere(descriptor):
            real_fsync(descriptor)
            settings.write_bytes(concurrent)

        module.os.fsync = save_elsewhere
        try:
            assert "changed while updating" in run(module)
        finally:
            module.os.fsync = real_fsync
        assert settings.read_bytes() == concurrent
        assert sorted(path.name for path in settings.parent.iterdir()) == ["DesktopEditors.conf"]
    print("PASS: OnlyOffice titlebar setting edits only the effective General key")


if __name__ == "__main__":
    main()
