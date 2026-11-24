#!/usr/bin/env python3
"""Check that the guarded DMS UI override launches only while intact, else falls back."""

import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch


def main():
    spec = importlib.util.spec_from_file_location("smooth_sliders", Path(__file__).with_name("configure-dms-smooth-sliders.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Launched(Exception):
        pass

    # The legacy 1.5.x installer applies every top-level shell-patches/*.patch
    # without fingerprint checks; guarded patches must stay out of its reach.
    legacy = {path.resolve() for path in (module.ROOT / "home/.config/DankMaterialShell/shell-patches").glob("*.patch")}
    guarded = {path.resolve() for patches in module.VERSION_PATCHES.values() for path in patches}
    assert all(path.is_file() for path in guarded), "guarded DMS patch missing"
    assert legacy.isdisjoint(guarded), "guarded DMS patch visible to install-dms-shell-overrides.sh"

    with tempfile.TemporaryDirectory(prefix="smooth-slider-check-") as directory:
        root = Path(directory)
        binary = root / "dms"
        binary.write_text("reviewed binary")
        for version, files in module.VERSION_FILES.items():
            output, target = root / version / "output", root / version / "staged"
            output.mkdir(parents=True)
            for path in files:
                (target / path.parent).mkdir(parents=True, exist_ok=True)
                (target / path).write_text("reviewed UI file")
            manifest = {"version": version, "patch_sha256": module.patch_digest(version), "files_sha256": module.patched_files(target, version), "dms_binary_sha256": module.digest(binary)}
            (target / "smooth-sliders.json").write_text(json.dumps(manifest))

            def launched(expected, running=version):
                recorded = []

                def fake_exec(program, arguments):
                    recorded.extend(arguments)
                    raise Launched()

                with patch.object(module.os, "execvp", fake_exec), patch.object(module.shutil, "which", return_value=str(binary)), patch.object(module.subprocess, "check_output", return_value=f"dms {running}\n"):
                    try:
                        module.launch(output)
                    except Launched:
                        pass
                assert recorded == expected, (version, recorded)

            launched(["dms", "run", "-d"])
            (output / "active.json").write_text(json.dumps({"target": str(target)}))
            launched(["dms", "-c", str(target), "run", "-d"])
            launched(["dms", "run", "-d"], running="v9.0.0")
            (target / "smooth-sliders.json").write_text(json.dumps({**manifest, "patch_sha256": "outdated-patches"}))
            launched(["dms", "run", "-d"])
            (target / "smooth-sliders.json").write_text(json.dumps(manifest))
            binary.write_text("updated binary, same version")
            launched(["dms", "run", "-d"])
            binary.write_text("reviewed binary")
            for path in files:
                (target / path).write_text("modified override")
                launched(["dms", "run", "-d"])
                (target / path).write_text("reviewed UI file")
                (target / path).unlink()
                launched(["dms", "run", "-d"])
                (target / path).write_text("reviewed UI file")
            launched(["dms", "-c", str(target), "run", "-d"])
            (output / "active.json").write_text("{corrupt")
            launched(["dms", "run", "-d"])
        unsupported = root / "unsupported"
        unsupported.mkdir()
        for retired in ("v2.0.0", "v9.0.0"):
            (unsupported / "VERSION").write_text(retired)
            try:
                module.stage(unsupported, root / "refused")
            except ValueError:
                pass
            else:
                raise AssertionError(f"Unsupported DMS {retired} source was accepted")
            assert not (root / "refused").exists()
    print(f"PASS: guarded override launch ({', '.join(module.VERSION_FILES)}), version/binary-update fallback, tamper/corrupt fallback, unsupported-source refusal (v2.0.0, v9.0.0)")


if __name__ == "__main__":
    main()
