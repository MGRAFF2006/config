#!/usr/bin/env python3
"""Portable repository checks: no packages installed and no services changed."""

import ast
import json
from pathlib import Path
import re
import subprocess
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def main():
    shell = []
    for directory in ("scripts", "home", "headless", "system", "ssh", "tailscale", "packages"):
        for path in sorted((ROOT / directory).rglob("*")):
            if any(part in (".git", "__pycache__", "src", "pkg", "hyprsplit") for part in path.parts):
                continue
            if path.is_symlink():
                assert path.exists(), f"Broken source link: {path.relative_to(ROOT)}"
                continue
            if not path.is_file() or path.suffix in (".pyc", ".patch"):
                continue
            if path.suffix == ".py":
                ast.parse(path.read_text(), filename=str(path))
            elif path.suffix == ".json":
                json.loads(path.read_text())
            elif path.suffix == ".toml":
                tomllib.loads(path.read_text())
            else:
                with path.open("rb") as stream:
                    first = stream.readline().decode("utf-8", errors="replace").strip()
                if path.suffix == ".sh" or first in ("#!/usr/bin/env bash", "#!/bin/bash", "#!/bin/sh"):
                    subprocess.run(["bash", "-n", str(path)], check=True)
                    if directory == "scripts" and path.suffix == ".sh":
                        shell.append(str(path))
    for path in sorted((ROOT / "packages").glob("*.txt")):
        seen = set()
        for line in path.read_text().splitlines():
            package = line.split("#", 1)[0].strip()
            if not package:
                continue
            assert re.fullmatch(r"[a-zA-Z0-9@._+:-]+", package), f"Invalid package in {path.name}: {package}"
            assert package not in seen, f"Duplicate package in {path.name}: {package}"
            seen.add(package)
    subprocess.run(["shellcheck", "--severity=warning", *shell], check=True)
    for check in ("check-agent-kit.py", "check-deployment.py"):
        subprocess.run(["python3", str(ROOT / "scripts" / check)], check=True)
    print("PASS: shell/Python syntax, JSON/TOML, package lists, shellcheck, deployment checks")


if __name__ == "__main__":
    main()
