#!/usr/bin/env python3
"""Check config deployment in a temporary home; never change the real machine."""

import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="config-deployment-") as directory:
        root = Path(directory)
        repo = root / "repo with spaces"
        shutil.copytree(source / "home", repo / "home", symlinks=True)
        shutil.copytree(source / "agent", repo / "agent", symlinks=True)
        shutil.copytree(source / "packages", repo / "packages", symlinks=True)
        (repo / "scripts").mkdir()
        for name in ("install.sh", "link-home.sh", "install-agent-kit.sh"):
            shutil.copy2(source / "scripts" / name, repo / "scripts" / name)
        binaries = root / "bin"
        binaries.mkdir()
        # Preview/check must never call system managers. Kit readiness probes are read-only.
        for tool in ("systemctl", "tailscale", "syncthing", "codex", "sudo", "yay"):
            stub = binaries / tool
            if tool in ("systemctl", "tailscale"):
                body = 'case "$*" in "--user is-active syncthing.service"|status) exit 0;; esac\nexit 99\n'
            elif tool in ("sudo", "yay"):
                body = "exit 99\n"
            else:
                body = "exit 0\n"
            stub.write_text("#!/bin/sh\n" + body)
            stub.chmod(0o755)
        # Make the installer platform check deterministic on Linux CI runners.
        grep = binaries / "grep"
        grep.write_text(
            '#!/bin/sh\nif [ "$*" = "-qx ID=arch /etc/os-release" ]; then exit 0; fi\nexec '
            + shlex.quote(shutil.which("grep")) + ' "$@"\n'
        )
        grep.chmod(0o755)
        env = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}")
        for variable in ("CODEX_HOME", "XDG_CONFIG_HOME", "AGENT_KIT_HOME", "MACHINE_TYPE"):
            env.pop(variable, None)

        def run(script, *args, expected=0):
            result = subprocess.run(
                ["bash", str(repo / "scripts" / script), *args],
                env=env, text=True, capture_output=True,
            )
            assert result.returncode == expected, result.stdout + result.stderr
            return result

        for machine in ("laptop", "desktop"):
            home = root / f"{machine} home"
            home.mkdir()
            env["CONFIG_LINK_HOME"] = str(home)
            (home / ".zshrc").write_text("original shell\n")
            (home / ".bashrc").symlink_to(root / "missing-old-target")
            (home / ".config/nvim").mkdir(parents=True)
            (home / ".config/nvim/custom.lua").write_text("keep editor\n")
            run("link-home.sh", "bad-machine", expected=2)
            run("install.sh", "bad-machine", expected=2)
            run("link-home.sh", machine, "--check", expected=1)
            run("install.sh", machine, "--dry-run")
            assert (home / ".zshrc").read_text() == "original shell\n"
            assert not (home / ".local").exists()
            run("install.sh", machine, expected=99)
            assert not (home / ".local").exists()  # A package failure stops deployment.
            run("link-home.sh", machine)
            backups = list((home / ".local/share/config-link-backups").iterdir())
            assert len(backups) == 1
            backup = backups[0]
            assert (backup / ".zshrc").read_text() == "original shell\n"
            assert (backup / ".bashrc").readlink() == root / "missing-old-target"
            assert (backup / ".config/nvim/custom.lua").read_text() == "keep editor\n"
            assert (home / ".config/alacritty/machine.toml").resolve() == repo / f"home/.config/alacritty/{machine}.toml"
            assert (home / ".config/zen-browser/userContent.css").is_symlink()
            assert (home / ".config/DankMaterialShell/theme_nord.json").is_symlink()
            assert (home / ".xinitrc").is_symlink() == (machine == "desktop")
            assert (home / ".config/systemd/user/laptop-lid-awake.service").is_symlink() == (machine == "laptop")
            run("link-home.sh", machine, "--check")
            run("link-home.sh", machine)
            assert list((home / ".local/share/config-link-backups").iterdir()) == backups
            assert (repo / "home/.config/alacritty/machine.toml").exists() is False

        # Inherited agent paths cannot escape an explicitly isolated home.
        env["CODEX_HOME"] = str(root / "real codex")
        env["XDG_CONFIG_HOME"] = str(root / "real config")
        run("link-home.sh", "desktop")
        assert not Path(env["CODEX_HOME"]).exists()
        assert not Path(env["XDG_CONFIG_HOME"]).exists()

        # Missing sources must fail before changing any existing destination.
        (repo / "home/.config/zen-browser/userContent.css").unlink()
        untouched = root / "untouched home"
        untouched.mkdir()
        env["CONFIG_LINK_HOME"] = str(untouched)
        run("link-home.sh", "laptop", expected=1)
        run("install.sh", "laptop", expected=1)
        assert list(untouched.iterdir()) == []
    print("PASS: both profiles, preview/check, invalid input, backups, broken links, idempotency, missing sources, no service changes, package failures stop installation")


if __name__ == "__main__":
    main()
