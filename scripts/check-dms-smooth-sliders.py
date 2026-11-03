#!/usr/bin/env python3
"""Check safe override launch/fallback; --ui exercises actual QML interpolation."""

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
    parser.add_argument("--ui", action="store_true")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("smooth_sliders", Path(__file__).with_name("configure-dms-smooth-sliders.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Launched(Exception):
        pass

    with tempfile.TemporaryDirectory(prefix="smooth-slider-check-") as directory:
        root = Path(directory)
        output, target = root / "output", root / "staged"
        output.mkdir()
        (target / module.SLIDER.parent).mkdir(parents=True)
        (target / module.SLIDER).write_text("reviewed slider")
        binary = root / "dms"
        binary.write_text("reviewed binary")
        manifest = {"version": "v2.0.0", "slider_sha256": module.digest(target / module.SLIDER), "dms_binary_sha256": module.digest(binary)}
        (target / "smooth-sliders.json").write_text(json.dumps(manifest))

        def launched(expected):
            recorded = []

            def fake_exec(program, arguments):
                recorded.extend(arguments)
                raise Launched()

            with patch.object(module.os, "execvp", fake_exec), patch.object(module.shutil, "which", return_value=str(binary)), patch.object(module.subprocess, "check_output", return_value="dms v2.0.0\n"):
                try:
                    module.launch(output)
                except Launched:
                    pass
            assert recorded == expected, recorded

        launched(["dms", "run", "-d"])
        (output / "active.json").write_text(json.dumps({"target": str(target)}))
        launched(["dms", "-c", str(target), "run", "-d"])
        binary.write_text("updated binary, same version")
        launched(["dms", "run", "-d"])
        binary.write_text("reviewed binary")
        (target / module.SLIDER).write_text("modified override")
        launched(["dms", "run", "-d"])
        (output / "active.json").write_text("{corrupt")
        launched(["dms", "run", "-d"])
        unsupported = root / "unsupported"
        unsupported.mkdir()
        (unsupported / "VERSION").write_text("v9.0.0")
        try:
            module.stage(unsupported, root / "refused")
        except ValueError:
            pass
        else:
            raise AssertionError("Unknown version was accepted")
        assert not (root / "refused").exists()
        print("PASS: guarded override launch, same-version binary update fallback, tamper/corrupt fallback, unknown-source refusal")

        if args.ui:
            runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
            source = Path((runtime / "dms.path").read_text().strip())
            staged = module.stage(source, root / "ui-staged")
            assert module.stage(staged, root / "ui-staged") == staged
            manifest_path = staged / "smooth-sliders.json"
            recorded = json.loads(manifest_path.read_text())
            recorded["dms_binary_sha256"] = "old-binary-build"
            manifest_path.write_text(json.dumps(recorded))
            assert module.stage(source, root / "ui-staged") == staged
            assert json.loads(manifest_path.read_text())["dms_binary_sha256"] == module.digest(Path(module.shutil.which("dms")))
            recorded = json.loads(manifest_path.read_text())
            recorded["source"] = str(root / "extraction-cleared-on-reboot")
            manifest_path.write_text(json.dumps(recorded))
            assert module.stage(staged, root / "ui-staged") == staged
            fixture = root / "fixture"
            fixture.mkdir()
            for name in ("DCommon", "Common", "Services", "Widgets", "Modules", "assets"):
                (fixture / name).symlink_to(staged / name, target_is_directory=True)
            (fixture / "shell.qml").write_text(Path(__file__).with_name("fixtures").joinpath("smooth-sliders.qml").read_text())
            isolated_runtime = root / "runtime"
            isolated_runtime.mkdir(mode=0o700)
            env = dict(os.environ, XDG_RUNTIME_DIR=str(isolated_runtime), QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="", QT_QUICK_BACKEND="software")
            for key in ("DISPLAY", "WAYLAND_DISPLAY", "HYPRLAND_INSTANCE_SIGNATURE", "DBUS_SESSION_BUS_ADDRESS"):
                env.pop(key, None)
            result = subprocess.run(["qs", "-p", str(fixture)], env=env, capture_output=True, text=True, timeout=20)
            logs = result.stdout + result.stderr
            assert result.returncode == 0 and "SMOOTH_SLIDER_PASS" in logs, logs
            print(next(line for line in logs.splitlines() if "SMOOTH_SLIDER_PASS" in line))
            print("PASS: actual DSlider intermediate/settled progress, rapid retarget, immediate values/commits, drag and reduced-motion bypass, reapply from staged source")


if __name__ == "__main__":
    main()
