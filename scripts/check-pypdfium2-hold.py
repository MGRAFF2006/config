#!/usr/bin/env python3
"""Check the pypdfium2 hold installer against fixture roots; never touch /etc."""

import os
from pathlib import Path
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
SCRIPT = SOURCE / "scripts/install-pypdfium2-hold.sh"
HOLD = (SOURCE / "system/pacman/pypdfium2-hold.conf").read_text()

# Portable pacman-conf stand-in: like pacman, it reports IgnorePkg only from
# [options], following Include lines there, and ignores it in repositories.
PACMAN_CONF = r'''#!/usr/bin/env python3
import sys
config = sys.argv[sys.argv.index("--config") + 1]
packages = []
def read(path, section):
    for raw in open(path):
        line = raw.split("#", 1)[0].strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif "=" in line and section == "options":
            key, value = (part.strip() for part in line.split("=", 1))
            if key == "Include":
                read(value, section)
            elif key == "IgnorePkg":
                packages.extend(value.split())
    return section
read(config, None)
print(" ".join(packages))
'''

BASE = "# fixture\n[options]\nHoldPkg = pacman\n\n[core]\nInclude = /etc/pacman.d/mirrorlist\n"


def main():
    with tempfile.TemporaryDirectory(prefix="config-pypdfium2-hold-") as directory:
        tmp = Path(directory)
        binaries = tmp / "bin"
        binaries.mkdir()
        (binaries / "pacman-conf").write_text(PACMAN_CONF)
        (binaries / "sudo").write_text("#!/bin/sh\nexit 99\n")  # Fixtures never escalate.
        for stub in binaries.iterdir():
            stub.chmod(0o755)
        env = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}")

        def fixture(name, conf):
            root = tmp / name
            (root / "etc").mkdir(parents=True)
            (root / "etc/pacman.conf").write_text(conf.replace("@HOLD@", str(root / "etc/pacman.d/pypdfium2-hold.conf")))
            return root

        def run(root, *args, expected=0):
            result = subprocess.run(
                ["bash", str(SCRIPT), *args], env=dict(env, PYPDFIUM2_HOLD_ROOT=str(root)),
                text=True, capture_output=True,
            )
            assert result.returncode == expected, (root.name, args, result.stdout + result.stderr)
            return result.stdout + result.stderr

        # A clean install adds one Include directly under [options] and is idempotent.
        root = fixture("clean", BASE)
        run(root, "--check", expected=1)
        run(root)
        run(root)
        conf = (root / "etc/pacman.conf").read_text()
        include = f"Include = {root}/etc/pacman.d/pypdfium2-hold.conf"
        assert conf == BASE.replace("[options]\n", f"[options]\n{include}\n"), conf
        assert (root / "etc/pacman.d/pypdfium2-hold.conf").read_text() == HOLD
        backups = sorted((root / "var/backups/config-pypdfium2-hold").iterdir())
        assert sorted((backup / "pacman.conf").read_text() for backup in backups) == sorted([BASE, conf])

        # An existing Include with pacman-equivalent spacing is not duplicated.
        root = fixture("spacing", "[options]\n  Include=@HOLD@   # managed\n[core]\n")
        run(root)
        assert (root / "etc/pacman.conf").read_text().count("pypdfium2-hold.conf") == 1

        # A symlinked pacman.conf is refused before anything is written.
        root = tmp / "symlink"
        (root / "etc").mkdir(parents=True)
        (root / "managed").mkdir()
        (root / "managed/pacman.conf").write_text(BASE)
        (root / "etc/pacman.conf").symlink_to("../managed/pacman.conf")
        assert "is a symlink" in run(root, expected=1)
        assert (root / "etc/pacman.conf").is_symlink()
        assert (root / "managed/pacman.conf").read_text() == BASE
        assert not (root / "etc/pacman.d").exists() and not (root / "var").exists()

        # A symlinked drop-in destination is refused as well.
        root = fixture("symlinked-drop-in", BASE)
        (root / "etc/pacman.d").mkdir()
        (root / "etc/pacman.d/pypdfium2-hold.conf").symlink_to(SOURCE / "system/pacman/pypdfium2-hold.conf")
        assert "is a symlink" in run(root, expected=1)
        assert (root / "etc/pacman.conf").read_text() == BASE

        # An ambiguous [options] layout is refused.
        root = fixture("two-options", BASE + "[options]\n")
        run(root, expected=1)
        assert not (root / "var").exists()

        # A misplaced Include (pacman ignores IgnorePkg in a repository) blocks
        # installation instead of suppressing the [options] insertion.
        misplaced = BASE + "Include = @HOLD@\n"
        root = fixture("misplaced", misplaced)
        assert "outside [options] (in: core)" in run(root, expected=1)
        assert not (root / "etc/pacman.d").exists() and not (root / "var").exists()

        # --check fails on the misplaced Include even when an independent hold
        # makes pacman-conf report the package.
        root = fixture("misplaced-independent-hold", misplaced.replace("[options]\n", "[options]\nIgnorePkg = python-pypdfium2\n"))
        (root / "etc/pacman.d").mkdir()
        (root / "etc/pacman.d/pypdfium2-hold.conf").write_text(HOLD)
        assert "python-pypdfium2" in subprocess.check_output(
            ["pacman-conf", "--config", str(root / "etc/pacman.conf"), "IgnorePkg"], env=env, text=True)
        assert "outside [options]" in run(root, "--check", expected=1)

        # A correct Include with a stale drop-in also fails the check.
        root = fixture("stale-drop-in", "[options]\nInclude = @HOLD@\n")
        (root / "etc/pacman.d").mkdir()
        (root / "etc/pacman.d/pypdfium2-hold.conf").write_text("IgnorePkg = other\n")
        assert "differs" in run(root, "--check", expected=1)
        run(root)
        run(root, "--check")

        run(tmp / "clean", "--dry-run")
        run(tmp / "clean", "--bogus", expected=2)
    print("PASS: pypdfium2 hold installer fixtures")


if __name__ == "__main__":
    main()
