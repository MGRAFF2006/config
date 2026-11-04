#!/usr/bin/env python3
"""Check safe override launch/fallback; --ui exercises actual QML interpolation."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from unittest.mock import patch


def isolated_ui_source(module, source, destination):
    """Recover pristine input in temporary storage, never in the active stage."""
    shutil.copytree(source, destination)
    for directory in [destination, *(path for path in destination.rglob("*") if path.is_dir())]:
        directory.chmod(directory.stat().st_mode | 0o700)
    manifest = destination / "smooth-sliders.json"
    if manifest.exists():
        recorded = json.loads(manifest.read_text())
        if "files_sha256" in recorded:
            assert recorded["patch_sha256"] == module.patch_digest()
            assert module.stage_intact(destination, recorded)
            patches = module.PATCHES
        else:
            # Existing slider-only stages can be used as isolated test input.
            assert recorded["patch_sha256"] == module.digest(module.PATCH)
            assert recorded["slider_sha256"] == module.digest(destination / module.SLIDER)
            patches = (module.PATCH,)
        for path in module.SUPPORTED_FILES:
            (destination / path).chmod(0o644)
        for patch_file in reversed(patches):
            subprocess.run(["patch", "--reverse", "--batch", "-p1", "-d", str(destination), "-i", str(patch_file)], check=True, capture_output=True, text=True)
        manifest.unlink()
        assert module.tree_digest(destination) == recorded["source_sha256"]
    return destination


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
        for path in module.SUPPORTED_FILES:
            (target / path.parent).mkdir(parents=True, exist_ok=True)
            (target / path).write_text("reviewed UI file")
        binary = root / "dms"
        binary.write_text("reviewed binary")
        manifest = {"version": "v2.0.0", "patch_sha256": module.patch_digest(), "files_sha256": module.patched_files(target), "dms_binary_sha256": module.digest(binary)}
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
        (target / "smooth-sliders.json").write_text(json.dumps({**manifest, "patch_sha256": "outdated-patches"}))
        launched(["dms", "run", "-d"])
        (target / "smooth-sliders.json").write_text(json.dumps(manifest))
        binary.write_text("updated binary, same version")
        launched(["dms", "run", "-d"])
        binary.write_text("reviewed binary")
        for path in module.SUPPORTED_FILES:
            (target / path).write_text("modified override")
            launched(["dms", "run", "-d"])
            (target / path).write_text("reviewed UI file")
            (target / path).unlink()
            launched(["dms", "run", "-d"])
            (target / path).write_text("reviewed UI file")
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
            input_hash = module.tree_digest(source)
            pristine = isolated_ui_source(module, source, root / "pristine")
            staged = module.stage(pristine, root / "ui-staged")
            assert module.stage(staged, root / "ui-staged") == staged
            manifest_path = staged / "smooth-sliders.json"
            recorded = json.loads(manifest_path.read_text())
            recorded["dms_binary_sha256"] = "old-binary-build"
            manifest_path.write_text(json.dumps(recorded))
            assert module.stage(pristine, root / "ui-staged") == staged
            assert json.loads(manifest_path.read_text())["dms_binary_sha256"] == module.digest(Path(module.shutil.which("dms")))
            recorded = json.loads(manifest_path.read_text())
            recorded["source"] = str(root / "extraction-cleared-on-reboot")
            manifest_path.write_text(json.dumps(recorded))
            assert module.stage(staged, root / "ui-staged") == staged
            # Reproduce a reboot-cleared extraction using a temporary stage.
            # Recovery and re-staging must leave that input untouched as well.
            reboot_hash = module.tree_digest(staged)
            recovered = isolated_ui_source(module, staged, root / "recovered")
            module.stage(recovered, root / "recovered-staged")
            assert module.tree_digest(staged) == reboot_hash
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
            assert module.tree_digest(source) == input_hash, "UI check changed its input source/stage"
            print(next(line for line in logs.splitlines() if "SMOOTH_SLIDER_PASS" in line))
            print("PASS: actual DSlider intermediate/settled progress, rapid retarget, immediate values/commits, drag and reduced-motion bypass, reapply from staged source")


if __name__ == "__main__":
    main()
