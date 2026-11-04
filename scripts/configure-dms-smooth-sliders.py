#!/usr/bin/env python3
"""Stage guarded DMS refinements: smooth sliders and inline quick-access pages."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
SLIDER = Path("DCommon/Widgets/DSlider.qml")
SUPPORTED_VERSION = "v2.0.0"
SUPPORTED_SLIDER = "0888dce6b3c9c1e7b748ee47470bd978700a8878793f071bf0641ccc63cc3adb"
PATCH = ROOT / "home/.config/DankMaterialShell/shell-patches/smooth-slider-level.patch"
PATCHES = (PATCH, PATCH.with_name("control-center-pages.patch"))
SUPPORTED_FILES = {
    SLIDER: SUPPORTED_SLIDER,
    Path("Modules/ControlCenter/Components/CcDetailPage.qml"): "dcf3d2e82ccdd5920b11d7b245d3b3b0c1876326b7e4a431fbb0753816e328d5",
    Path("Modules/ControlCenter/ControlCenterContent.qml"): "cd62fce37d92706a1f9db61edf1ba65e4af6071a72b59a8114fcedc82c3fe6ce",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def patch_digest():
    return hashlib.sha256(b"".join(bytes.fromhex(digest(path)) for path in PATCHES)).hexdigest()


def patched_files(root):
    return {str(path): digest(root / path) for path in SUPPORTED_FILES}


def stage_intact(root, manifest):
    return manifest.get("files_sha256") == patched_files(root)


def tree_digest(root):
    result = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            result.update(str(path.relative_to(root)).encode() + b"\0")
            result.update(bytes.fromhex(digest(path)))
    return result.hexdigest()


def stage(source, output):
    # dms.path points at our staged UI after activation. Reapply from its
    # recorded pristine source rather than patching the override twice.
    if (source / "smooth-sliders.json").is_file():
        previous = json.loads((source / "smooth-sliders.json").read_text())
        original = Path(previous["source"])
        if not original.exists():
            # /run is cleared on reboot. An unchanged, verified stage remains
            # reusable without its now-absent extraction directory.
            if previous["version"] == SUPPORTED_VERSION and previous["patch_sha256"] == patch_digest() and previous.get("dms_binary_sha256") == digest(Path(shutil.which("dms"))) and stage_intact(source, previous):
                return source
            raise ValueError("Pristine source is unavailable and the staged UI no longer matches. Launch built-in DMS, then stage again.")
        source = original
    version = (source / "VERSION").read_text().strip()
    if version != SUPPORTED_VERSION or patched_files(source) != {str(path): value for path, value in SUPPORTED_FILES.items()}:
        raise ValueError("DMS version/UI differs from the reviewed 2.0.0 source; review and update the patches before staging.")
    source_hash, patch_hash = tree_digest(source), patch_digest()
    target = output / (version + "-" + source_hash[:12] + "-" + patch_hash[:8])
    if target.exists():
        manifest = json.loads((target / "smooth-sliders.json").read_text())
        if manifest["source_sha256"] != source_hash or manifest["patch_sha256"] != patch_hash or not stage_intact(target, manifest):
            raise ValueError("Existing UI override was modified; preserve it and use a separate output directory.")
        binary_hash = digest(Path(shutil.which("dms")))
        if manifest.get("dms_binary_sha256") != binary_hash:
            # Explicit re-staging has just verified the current pristine UI.
            # A binary-only rebuild may keep the same source/target directory.
            manifest["dms_binary_sha256"] = binary_hash
            (target / "smooth-sliders.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return target
    output.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".smooth-sliders-", dir=output))
    try:
        shutil.copytree(source, temporary, dirs_exist_ok=True)
        for directory in [temporary, *(path for path in temporary.rglob("*") if path.is_dir())]:
            directory.chmod(directory.stat().st_mode | 0o700)
        for path in SUPPORTED_FILES:
            (temporary / path).chmod(0o644)
        for patch in PATCHES:
            subprocess.run(["patch", "--dry-run", "--batch", "-p1", "-d", str(temporary), "-i", str(patch)], check=True, capture_output=True, text=True)
            subprocess.run(["patch", "--batch", "-p1", "-d", str(temporary), "-i", str(patch)], check=True, capture_output=True, text=True)
        manifest = {
            "version": version, "source": str(source), "source_sha256": source_hash,
            "patch_sha256": patch_hash, "files_sha256": patched_files(temporary),
            "dms_binary_sha256": digest(Path(shutil.which("dms"))),
        }
        (temporary / "smooth-sliders.json").write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return target


def launch(output):
    active = output / "active.json"
    candidate = None
    if active.exists():
        try:
            target = Path(json.loads(active.read_text())["target"])
            manifest = json.loads((target / "smooth-sliders.json").read_text())
            version = subprocess.check_output(["dms", "version"], text=True).strip()
            match = re.search(r"v\d+\.\d+\.\d+(?:[-+][\w.-]+)?", version)
            if match and match[0] == manifest["version"] and manifest["patch_sha256"] == patch_digest() and digest(Path(shutil.which("dms"))) == manifest.get("dms_binary_sha256") and stage_intact(target, manifest):
                candidate = target
        except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
            print(f"Cannot validate DMS UI override: {error}", file=sys.stderr)
        if candidate is None:
            print("DMS changed or the UI override is unavailable; using the built-in UI. Re-run configure-dms-smooth-sliders.py --apply after reviewing the updated source.", file=sys.stderr, flush=True)
    else:
        print("No DMS UI override staged; using the built-in DMS UI.", file=sys.stderr, flush=True)
    if candidate is not None:
        print(f"Launching reviewed DMS UI: {candidate}", flush=True)
        os.execvp("dms", ["dms", "-c", str(candidate), "run", "-d"])
    os.execvp("dms", ["dms", "run", "-d"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="Defaults to the running DMS's extracted UI")
    parser.add_argument("--output", type=Path, default=Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "dms-ui-overrides")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Stage the override without changing the running shell")
    mode.add_argument("--launch", action="store_true", help="Launch the compatible override, falling back to the built-in UI after updates")
    args = parser.parse_args()
    if args.launch:
        launch(args.output)
        return
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    source = args.source_dir or Path((runtime / "dms.path").read_text().strip())
    source = source.resolve(strict=True)
    if not args.apply:
        print(f"Source: {source}\nOutput: {args.output}\nUse --apply to stage. This does not restart the running shell.")
        return
    target = stage(source, args.output)
    args.output.mkdir(parents=True, exist_ok=True)
    pointer = args.output / "active.json"
    fd, temporary = tempfile.mkstemp(prefix=".active-", dir=args.output)
    with os.fdopen(fd, "w") as stream:
        json.dump({"target": str(target)}, stream)
        stream.write("\n")
    os.replace(temporary, pointer)
    print(f"Staged: {target}")
    print("Launch: " + shlex.join(["dms", "-c", str(target), "run", "-d"]))
    print("Updates require re-staging from the current built-in UI; changed source versions fail closed.")


if __name__ == "__main__":
    main()
