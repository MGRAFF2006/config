#!/usr/bin/env python3
"""Stage the reviewed DMS 2.0 greeter appearance fix; launch safely after updates."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
BINARY = Path("/usr/bin/dms-greeter")
# dms-greeter 2.0.0, commit 0044526f90b584916548f0a17dbf31764a6db530.
BINARY_SHA256 = "805a67cdc4d2137cf4ceaeb4361f72a229a3198d106354d8dd2c922579424cba"
SOURCE_SHA256 = "cd423624a7b5679d4c767b296b11e24f40007e6c868dd0d324e7fad1cafbe0d8"
PATCHED_SHA256 = "d63b97f68811eeac307e38be7f7c84569ad33243f889e54bb01a457ce0f6fe91"
MANIFEST = "greeter-appearance.json"
PATCH = ROOT / "home/.config/DankMaterialShell/shell-patches/greeter-appearance.patch"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tree_digest(root):
    result = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Unexpected symlink in greeter UI: {path}")
        if path.is_file() and path.relative_to(root).as_posix() != MANIFEST:
            result.update(str(path.relative_to(root)).encode() + b"\0")
            result.update(bytes.fromhex(digest(path)))
    return result.hexdigest()


def validate(output):
    manifest = json.loads((output / MANIFEST).read_text())
    if digest(BINARY) != BINARY_SHA256 or manifest["binary_sha256"] != BINARY_SHA256:
        raise ValueError("The greeter binary changed; review and re-stage its UI")
    if manifest["ui_sha256"] != PATCHED_SHA256 or tree_digest(output) != PATCHED_SHA256:
        raise ValueError("The staged greeter UI changed or is incomplete")


def stage(source, output):
    if digest(BINARY) != BINARY_SHA256 or tree_digest(source) != SOURCE_SHA256:
        raise ValueError("Greeter binary/source differs from the reviewed 2.0.0 build")
    if output.exists():
        validate(output)
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".greeter-ui-", dir=output.parent))
    try:
        shutil.copytree(source, temporary, dirs_exist_ok=True)
        for path in [temporary, *temporary.rglob("*")]:
            path.chmod(0o755 if path.is_dir() else 0o644)
        subprocess.run(["patch", "--batch", "--fuzz=0", "-p1", "-d", str(temporary), "-i", str(PATCH)], check=True, capture_output=True, text=True)
        patched_hash = tree_digest(temporary)
        if patched_hash != PATCHED_SHA256:
            raise ValueError("Appearance patch no longer produces the reviewed greeter UI")
        (temporary / MANIFEST).write_text(json.dumps({
            "binary_sha256": BINARY_SHA256, "source_sha256": SOURCE_SHA256,
            "ui_sha256": patched_hash, "source": str(source),
        }, indent=2) + "\n")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return output


def launch(output, native_args):
    command = [str(BINARY)]
    try:
        validate(output)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Greeter appearance override unavailable ({error}); using built-in UI.", file=sys.stderr, flush=True)
        # An inherited development override must not defeat the safe fallback.
        os.environ.pop("DMS_GREETER_SHELL_DIR", None)
    else:
        command += ["--shell-dir", str(output)]
    os.execv(str(BINARY), command + native_args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--launch", action="store_true")
    parser.add_argument("native_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    native_args = args.native_args[1:] if args.native_args[:1] == ["--"] else args.native_args
    if args.launch:
        launch(args.output, native_args)
        return
    if native_args:
        parser.error("Native greeter arguments require --launch")
    source = args.source_dir
    if source is None:
        cache = Path("/var/cache/dms-greeter/.cache/dms-greeter-shell")
        sources = [path for path in cache.glob("*") if path.is_dir() and tree_digest(path) == SOURCE_SHA256]
        if len(sources) != 1:
            parser.error("Pass --source-dir pointing to the reviewed extracted greeter UI")
        source = sources[0]
    if not args.apply:
        print(f"Source: {source}\nOutput: {args.output}\nUse --apply to stage; this does not restart the greeter.")
        return
    print(stage(source.resolve(strict=True), args.output.resolve()))


if __name__ == "__main__":
    main()
