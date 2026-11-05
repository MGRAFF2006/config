#!/usr/bin/env python3
"""Check that incompatible or modified greeter overrides fall back safely."""

import importlib.util
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch


def main():
    script = Path(__file__).with_name("configure-dms-greeter-ui.py")
    spec = importlib.util.spec_from_file_location("greeter_ui", script)
    ui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ui)
    with tempfile.TemporaryDirectory(prefix="greeter-ui-check-") as directory:
        root = Path(directory)
        ui.BINARY = root / "dms-greeter"
        ui.BINARY.write_bytes(b"installed greeter build")
        ui.BINARY_SHA256 = ui.digest(ui.BINARY)
        output = root / "reviewed-ui"
        output.mkdir()
        qml = output / "shell.qml"
        qml.write_text("// reviewed fixture\n")
        ui.PATCHED_SHA256 = ui.tree_digest(output)
        manifest = output / ui.MANIFEST
        manifest.write_text(json.dumps({"binary_sha256": ui.BINARY_SHA256, "ui_sha256": ui.PATCHED_SHA256}))
        native = ["--command", "hyprland", "-C", "/etc/greetd/dms-hypr.lua", "--cache-dir", "/var/cache/dms-greeter"]

        def launched():
            with patch.object(ui.os, "execv") as execute:
                ui.launch(output, native)
                return execute.call_args.args

        assert launched() == (str(ui.BINARY), [str(ui.BINARY), "--shell-dir", str(output), *native])
        # Updating the package must never start the old QML against a new backend.
        ui.BINARY.write_bytes(b"upgraded greeter build")
        with patch.dict(os.environ, {"DMS_GREETER_SHELL_DIR": "/stale/development/ui"}):
            assert launched() == (str(ui.BINARY), [str(ui.BINARY), *native])
            assert "DMS_GREETER_SHELL_DIR" not in os.environ
        ui.BINARY.write_bytes(b"installed greeter build")
        # Protect all staged files, including files the appearance patch never edits.
        qml.write_text("// locally modified\n")
        assert launched() == (str(ui.BINARY), [str(ui.BINARY), *native])
        # Editing the manifest alongside the UI must not bypass the reviewed hash.
        manifest.write_text(json.dumps({"binary_sha256": ui.BINARY_SHA256, "ui_sha256": ui.tree_digest(output)}))
        assert launched() == (str(ui.BINARY), [str(ui.BINARY), *native])
        manifest.write_text("{corrupt")
        assert launched() == (str(ui.BINARY), [str(ui.BINARY), *native])
        # Refuse unreviewed pristine source without creating or overwriting output.
        absent = root / "not-created"
        try:
            ui.stage(output, absent)
        except ValueError:
            pass
        else:
            raise AssertionError("Unreviewed source was accepted")
        assert not absent.exists()
    print("PASS: greeter override preserves launch flags and falls back after binary/UI/manifest changes; unreviewed staging refused")


if __name__ == "__main__":
    main()
