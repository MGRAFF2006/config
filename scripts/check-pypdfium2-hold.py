#!/usr/bin/env python3
"""Check the pypdfium2 hold installer against fixture roots; never touch /etc.

The installer only installs the drop-in. Its --check relies on the real
pacman-conf, so those cases run only where pacman is installed (not on CI).
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
SCRIPT = SOURCE / "scripts/install-pypdfium2-hold.sh"
HOLD = (SOURCE / "system/pacman/pypdfium2-hold.conf").read_text()
MIRROR = "Server = https://mirror.invalid/core\n"


def main():
    with tempfile.TemporaryDirectory(prefix="config-pypdfium2-hold-") as directory:
        tmp = Path(directory)
        binaries = tmp / "bin"
        binaries.mkdir()
        (binaries / "sudo").write_text("#!/bin/sh\nexit 99\n")  # Fixtures never escalate.
        (binaries / "sudo").chmod(0o755)
        env = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}")

        def fixture(name, conf):
            root = tmp / name
            (root / "etc/pacman.d").mkdir(parents=True)
            (root / "etc/pacman.d/mirrorlist").write_text(MIRROR)
            conf = conf.replace("@D@", str(root / "etc/pacman.d"))
            (root / "etc/pacman.conf").write_bytes(conf.encode())
            return root

        def run(root, *args, expected=0):
            result = subprocess.run(
                ["bash", str(SCRIPT), *args], env=dict(env, PYPDFIUM2_HOLD_ROOT=str(root)),
                text=True, capture_output=True,
            )
            assert result.returncode == expected, (root.name, args, result.stdout + result.stderr)
            return result.stdout + result.stderr

        base = "[options]\nHoldPkg = pacman\n\n[core]\nInclude = @D@/mirrorlist\n"
        include = "Include = @D@/pypdfium2-hold.conf\n"

        # Install writes only the drop-in, leaves pacman.conf alone, prints the
        # exact Include line and is idempotent without backups of equal files.
        root = fixture("clean", base)
        drop_in = root / "etc/pacman.d/pypdfium2-hold.conf"
        assert f"  Include = {drop_in}\n" in run(root)
        run(root)
        assert drop_in.read_text() == HOLD
        assert (root / "etc/pacman.conf").read_text() == base.replace("@D@", str(root / "etc/pacman.d"))
        assert not (root / "var").exists()

        # A differing regular file is backed up, then replaced.
        drop_in.write_text("IgnorePkg = other\n")
        run(root)
        backups = list((root / "var/backups/config-pypdfium2-hold").glob("*/pypdfium2-hold.conf"))
        assert [backup.read_text() for backup in backups] == ["IgnorePkg = other\n"], backups
        assert drop_in.read_text() == HOLD

        # A symlinked pacman.conf gets instructions for its resolved target.
        root = tmp / "symlinked-pacman-conf"
        (root / "etc").mkdir(parents=True)
        (root / "managed").mkdir()
        (root / "managed/pacman.conf").write_text(base)
        (root / "etc/pacman.conf").symlink_to("../managed/pacman.conf")
        assert f"sudoedit {root / 'managed/pacman.conf'}\n" in run(root)
        assert (root / "etc/pacman.conf").is_symlink()

        # A directory or symlink at the destination is refused before writes,
        # in --dry-run as well.
        for name, make in (("directory", Path.mkdir), ("symlink", lambda path: path.symlink_to(SOURCE / "README.md"))):
            root = fixture(f"{name}-destination", base)
            make(root / "etc/pacman.d/pypdfium2-hold.conf")
            for args in ((), ("--dry-run",)):
                assert "not a regular file" in run(root, *args, expected=1)
            assert not (root / "var").exists()
        assert not any((tmp / "directory-destination/etc/pacman.d/pypdfium2-hold.conf").iterdir())

        root = fixture("dry-run", base)
        run(root, "--dry-run")
        assert not (root / "etc/pacman.d/pypdfium2-hold.conf").exists()
        run(root, "--bogus", expected=2)
        run(root, "--check", "extra", expected=2)
        assert "is missing" in run(root, "--check", expected=1)

        if not shutil.which("pacman-conf"):
            print("SKIP: pacman-conf is not installed; --check cases need the real pacman parser")
            print("PASS: pypdfium2 hold installer fixtures")
            return

        def check(name, conf, expected, message="", drop_in=HOLD):
            root = fixture(name, conf)
            (root / "etc/pacman.d/pypdfium2-hold.conf").write_text(drop_in)
            output = run(root, "--check", expected=expected)
            assert message in output, (name, output)

        independent = "[options]\nIgnorePkg = python-pypdfium2\n"
        options = base.replace("[options]\n", "[options]\n" + include)
        check("included", options, 0, "PASS")
        check("crlf-include", base.replace("[options]\n", "[options]\r\n  Include=@D@/pypdfium2-hold.conf  \r\n"), 0, "PASS")
        check("not-included", base, 1, "does not report")
        check("stale-drop-in", options, 1, "differs", drop_in="IgnorePkg = other\n")
        # An unrelated hold must not make a missing or misplaced include pass.
        check("independent-hold-only", base.replace("[options]\n", independent), 1, "stays held")
        check("misplaced", base.replace("[options]\n", independent) + include, 1, "warns about")
        # Pacman strips the CR, so this include sits in [core], not [options].
        check("crlf-section", independent + "[core]\r\n" + include, 1, "warns about")
        # A repository glob that picks up the new drop-in is reported too.
        check("repository-glob", options + "Include = @D@/*.conf\n", 1, "warns about")
        # Pacman keeps a trailing comment as part of the filename.
        check("comment-suffix", base.replace("[options]\n", "[options]\n" + include.replace("\n", " # managed\n")), 1, "cannot parse")
    print("PASS: pypdfium2 hold installer fixtures")


if __name__ == "__main__":
    main()
