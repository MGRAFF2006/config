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
        shutil.copytree(source / "headless", repo / "headless", symlinks=True)
        shutil.copytree(source / "ssh", repo / "ssh", symlinks=True)
        shutil.copytree(source / "systemd", repo / "systemd", symlinks=True)
        shutil.copytree(source / "system", repo / "system", symlinks=True)
        (repo / "scripts").mkdir()
        for name in ("install.sh", "link-home.sh", "install-agent-kit.sh", "install-bluetooth-config.sh", "configure-ssh.py"):
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
            (home / ".ssh").mkdir()
            (home / ".ssh/config").write_text("IdentityFile ~/.ssh/local-only-key\nHost custom\n    HostName custom.invalid\n")
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
            assert len(backups) == 2  # Home links and local SSH config have separate backups.
            backup = next(p for p in backups if (p / ".zshrc").exists())
            ssh_backup = next(p for p in backups if (p / ".ssh/config").exists())
            assert (ssh_backup / ".ssh/config").read_text().startswith("IdentityFile ~/.ssh/local-only-key")
            assert "HostName custom.invalid" in (home / ".ssh/config").read_text()
            effective = subprocess.check_output(["ssh", "-T", "-F", str(home / ".ssh/config"), "-G", "custom"], text=True)
            assert "hostname custom.invalid" in effective
            assert "identityfile ~/.ssh/local-only-key" in effective
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

        headless = root / "headless home"
        headless.mkdir()
        env["CONFIG_LINK_HOME"] = str(headless)
        run("link-home.sh", "homelab-dev", "--dry-run")
        assert list(headless.iterdir()) == []
        run("link-home.sh", "homelab-dev")
        run("link-home.sh", "homelab-dev", "--check")
        assert (headless / ".zshenv").resolve() == repo / "headless/zshenv"
        assert (headless / ".config/mise/config.toml").resolve() == repo / "headless/mise.toml"
        assert not (headless / ".config/alacritty").exists()
        assert not (headless / ".config/hypr").exists()
        env["CONFIG_LINK_HOME"] = str(home)

        system = root / "system root"
        system.mkdir()
        env["CONFIG_SYSTEM_ROOT"] = str(system)
        dest = system / "etc/modprobe.d/btusb-no-autosuspend.conf"
        dest.parent.mkdir(parents=True)
        dest.write_text("original module options\n")
        run("install-bluetooth-config.sh", "--dry-run")
        assert dest.read_text() == "original module options\n"
        run("install-bluetooth-config.sh", "--check", expected=1)
        run("install-bluetooth-config.sh")
        run("install-bluetooth-config.sh", "--check")
        backups = list((system / "var/backups/config-bluetooth").iterdir())
        assert len(backups) == 1
        assert (backups[0] / "etc/modprobe.d/btusb-no-autosuspend.conf").read_text() == "original module options\n"
        run("install-bluetooth-config.sh")
        assert list((system / "var/backups/config-bluetooth").iterdir()) == backups

        # Resume helpers must use isolated build roots, omit debug archives,
        # and refuse missing runtime archives before attempting installation.
        resume_bin = root / "resume-bin"
        resume_bin.mkdir()
        bodies = {
            "sudo": 'printf "%s\\n" "$*" >> "$CONFIG_TEST_LOG"\n',
            "pacman": "exit 0\n",
            "makepkg": 'touch "$PKGDEST/meshroom-1-1-x86_64.pkg.tar.zst"\n',
            "ls": "exit 0\n", "grep": "exit 0\n",
            "meshroom": "exit 0\n", "aliceVision_depthMapEstimation": "exit 0\n",
        }
        for name, body in bodies.items():
            binary = resume_bin / name
            binary.write_text("#!/bin/sh\n" + body)
            binary.chmod(0o755)
        for name in ("resume-after-alicevision.sh", "resume-meshroom-only.sh"):
            build_root = root / name
            cache = build_root / "pkgs"
            cache.mkdir(parents=True)
            log = build_root / "commands.log"
            resume_env = dict(os.environ, PATH=f"{resume_bin}:{os.environ['PATH']}",
                              BUILD_ROOT=str(build_root), CONFIG_TEST_LOG=str(log))
            resume_env.pop("PKGDEST", None)
            for archive in ("alice-vision-1-1-x86_64.pkg.tar.zst", "alice-vision-debug-1-1-x86_64.pkg.tar.zst",
                            "meshroom-debug-1-1-x86_64.pkg.tar.zst"):
                (cache / archive).touch()
            command = ["bash", str(repo / "packages/aur-builds" / name)]
            result = subprocess.run(command, env=resume_env, capture_output=True, text=True)
            assert result.returncode == 0, result.stdout + result.stderr
            assert "-debug-" not in log.read_text()
            if name == "resume-after-alicevision.sh":
                (cache / "alice-vision-1-1-x86_64.pkg.tar.zst").unlink()
                before = log.read_text()
                result = subprocess.run(command, env=resume_env, capture_output=True, text=True)
                assert result.returncode != 0
                assert log.read_text() == before

        # Inherited agent paths cannot escape an explicitly isolated home.
        env["CODEX_HOME"] = str(root / "real codex")
        env["XDG_CONFIG_HOME"] = str(root / "real config")
        run("link-home.sh", "desktop")
        assert not Path(env["CODEX_HOME"]).exists()
        assert not Path(env["XDG_CONFIG_HOME"]).exists()

        build_script = (repo / "packages/aur-builds/install-meshroom-stack.sh").read_text()
        cache_function = build_script[build_script.index("pkg_built() {"):build_script.index("build_aur_pkg() {")]
        cache = root / "package cache"
        cache.mkdir()
        (cache / "example-debug-1-x86_64.pkg.tar.zst").touch()
        cache_env = dict(env, PKGDEST=str(cache))
        subprocess.run(["bash", "-c", cache_function + "\nif pkg_built example; then exit 1; fi"], env=cache_env, check=True)
        (cache / "example-1-x86_64.pkg.tar.zst").touch()
        subprocess.run(["bash", "-c", cache_function + "\npkg_built example"], env=cache_env, check=True)

        # Missing sources must fail before changing any existing destination.
        (repo / "home/.config/zen-browser/userContent.css").unlink()
        untouched = root / "untouched home"
        untouched.mkdir()
        env["CONFIG_LINK_HOME"] = str(untouched)
        run("link-home.sh", "laptop", expected=1)
        run("install.sh", "laptop", expected=1)
        assert list(untouched.iterdir()) == []
    print("PASS: workstation/headless/system profiles, preview/check, invalid input, backups, broken links, idempotency, missing sources, no service changes, package failures stop installation")


if __name__ == "__main__":
    main()
