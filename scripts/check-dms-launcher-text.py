#!/usr/bin/env python3
"""Exercise actual launcher rows and tiles with synthetic clipboard data, in the private agent desktop."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="Pristine DMS UI; defaults to the running UI")
    parser.add_argument("--unpatched", action="store_true", help="Reproduce the failure against pristine components")
    parser.add_argument("--evidence", type=Path, help="Save the rendered fixture as a PNG")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("ui_override", Path(__file__).with_name("configure-dms-smooth-sliders.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    source = args.source_dir or Path((runtime / "dms.path").read_text().strip())
    original_hash = module.tree_digest(source)
    with tempfile.TemporaryDirectory(prefix="launcher-text-check-") as directory:
        root = Path(directory)
        staged = source if args.unpatched else module.stage(source, root / "staged")
        if not args.unpatched:
            assert module.stage(staged, root / "staged") == staged
            # Each patched renderer must be covered by the launch guard.
            manifest = json.loads((staged / "smooth-sliders.json").read_text())
            output = root / "staged"
            (output / "active.json").write_text(json.dumps({"target": str(staged)}))

            class Launched(Exception):
                pass

            def launch_arguments():
                with patch.object(module.os, "execvp", side_effect=Launched) as execute:
                    try:
                        module.launch(output)
                    except Launched:
                        pass
                return execute.call_args.args[1]

            assert launch_arguments() == ["dms", "-c", str(staged), "run", "-d"]
            for name in manifest["files_sha256"]:
                target = staged / name
                original = target.read_bytes()
                target.write_bytes(original + b"\n// altered\n")
                assert launch_arguments() == ["dms", "run", "-d"]
                target.write_bytes(original)
            manifest["version"] = "v9.0.0"
            (staged / "smooth-sliders.json").write_text(json.dumps(manifest))
            assert launch_arguments() == ["dms", "run", "-d"]
        fixture = root / "fixture"
        fixture.mkdir()
        for entry in staged.iterdir():
            if entry.is_dir():
                (fixture / entry.name).symlink_to(entry, target_is_directory=True)
        (fixture / "shell.qml").write_text(Path(__file__).with_name("fixtures").joinpath("launcher-text-bounds.qml").read_text())
        # PanelWindow imports need a real backend; use only the isolated desktop.
        if runtime != Path(f"/run/user/{os.getuid()}/agent-desktop"):
            raise RuntimeError("Run with agent-desktop run; the human desktop is not an allowed target")
        env = dict(os.environ, QT_QPA_PLATFORM="xcb", QT_QPA_PLATFORMTHEME="", QT_QUICK_BACKEND="software",
                   XDG_CONFIG_HOME=str(root / "config"), XDG_STATE_HOME=str(root / "state"),
                   XDG_DATA_HOME=str(root / "data"), XDG_CACHE_HOME=str(root / "cache"))
        if args.evidence:
            env["DMS_LAUNCHER_EVIDENCE"] = str(args.evidence.resolve())
        try:
            result = subprocess.run(["qs", "-p", str(fixture)], env=env, capture_output=True, text=True, timeout=25)
        except subprocess.TimeoutExpired as error:
            raise AssertionError((error.stdout or b"").decode() + (error.stderr or b"").decode()) from error
        logs = result.stdout + result.stderr
        assert result.returncode == 0 and "LAUNCHER_TEXT_PASS" in logs, logs
        assert module.tree_digest(source) == original_hash, "Check changed the input UI"
        print(next(line for line in logs.splitlines() if "LAUNCHER_TEXT_PASS" in line))
        print("PASS: renderer tamper/version fallback, repeat staging, unchanged input source")


if __name__ == "__main__":
    main()
