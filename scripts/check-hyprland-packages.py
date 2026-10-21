#!/usr/bin/env python3
"""Exercise optional-session install/rollback with fake system managers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="hyprland-packages-") as directory:
        root = Path(directory)
        repo = root / "repo"
        for name in ("scripts", "home", "agent", "packages", "headless", "system", "systemd", "ssh"):
            shutil.copytree(source / name, repo / name, symlinks=True,
                            ignore=shutil.ignore_patterns(".git", "__pycache__", "src", "pkg", "*.pkg.tar.*"))
        home = root / "home"
        home.mkdir()
        binaries = root / "bin"
        binaries.mkdir()
        base = ["plasma-meta", "wl-clipboard", "nautilus", "greetd", "git"]
        package_state = root / "installed.json"
        package_state.write_text(json.dumps(base))
        manager = '''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
p = Path(os.environ['CONFIG_TEST_PACKAGES'])
installed = set(json.loads(p.read_text()))
if os.environ.get('CONFIG_TEST_FAIL') and sys.argv[1] == '-Syu':
    raise SystemExit(42)
if sys.argv[1:] == ['-Qq']:
    print('\\n'.join(sorted(installed)))
    raise SystemExit(0)
names = {a for a in sys.argv[2:] if not a.startswith('-')}
if sys.argv[1] in ('-Syu', '-S'):
    installed.update(names)
elif sys.argv[1] == '-R':
    installed.difference_update(names)
else:
    raise SystemExit(99)
p.write_text(json.dumps(sorted(installed)))
'''
        for name in ("pacman", "yay"):
            (binaries / name).write_text(manager)
        (binaries / "sudo").write_text('#!/bin/sh\n[ "$1" = pacman ] || exit 99\nexec "$@"\n')
        (binaries / "systemctl").write_text('#!/bin/sh\ncase "$*" in "--user disable dms.service"|"--user daemon-reload") exit 0;; esac\nexit 1\n')
        for name in ("xdg-mime", "kwriteconfig6"):
            (binaries / name).write_text("#!/bin/sh\nexit 0\n")
        for binary in binaries.iterdir():
            binary.chmod(0o755)
        state = root / "state"
        env = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}",
                   CONFIG_LINK_HOME=str(home), CONFIG_DEPLOY_STATE_HOME=str(state),
                   XDG_CONFIG_HOME=str(home / ".config"), XDG_STATE_HOME=str(root / "session"),
                   CONFIG_TEST_PACKAGES=str(package_state), XDG_CURRENT_DESKTOP="KDE")

        def run(script, *args, expected=0):
            result = subprocess.run(["bash", str(repo / "scripts" / script), *args],
                                    env=env, capture_output=True, text=True)
            assert result.returncode == expected, result.stdout + result.stderr

        run("install-hyprland-dms.sh", "desktop", "--with-greeter", expected=2)
        run("install-hyprland-dms.sh", "laptop", "--dry-run")
        assert not state.exists()
        assert list(home.iterdir()) == []
        env["CONFIG_TEST_FAIL"] = "1"
        run("install-hyprland-dms.sh", "laptop", expected=42)
        assert set(json.loads(package_state.read_text())) == set(base)
        assert not (home / ".config/DankMaterialShell/settings.json").exists()
        env.pop("CONFIG_TEST_FAIL")
        run("remove-hyprland-dms.sh")
        run("install-hyprland-dms.sh", "laptop")
        manifest = state / "hyprland-dms-packages.txt"
        introduced = set(manifest.read_text().splitlines())
        assert "hyprland" in introduced
        assert not introduced.intersection(base)
        previous = manifest.read_text()
        run("install-hyprland-dms.sh", "laptop")
        assert manifest.read_text() == previous
        run("remove-hyprland-dms.sh", "--dry-run")
        assert manifest.exists()
        env["XDG_CURRENT_DESKTOP"] = "Hyprland"
        run("remove-hyprland-dms.sh", expected=1)
        assert manifest.exists()
        env["XDG_CURRENT_DESKTOP"] = "KDE"
        run("remove-hyprland-dms.sh")
        assert set(json.loads(package_state.read_text())) == set(base)
        assert not manifest.exists()
        assert (home / ".config/DankMaterialShell/settings.json").exists()
        run("remove-hyprland-dms.sh", expected=1)
    print("PASS: Hyprland preview, package journal, repeated installs, protected running session, rollback preserves Plasma and settings")


if __name__ == "__main__":
    main()
