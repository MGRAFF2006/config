#!/usr/bin/env python3
"""Check that installing greeter appearance preserves login behavior."""

import importlib.util
import os
from pathlib import Path
import shlex
import tempfile
import tomllib


def main():
    spec = importlib.util.spec_from_file_location("greeter_theme", Path(__file__).with_name("install-dms-greeter-theme.py"))
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    original = '''# Keep local greeter configuration and its session policy.
[terminal]
vt = 3
[default_session]
command = "/usr/bin/dms-greeter --command hyprland -C /etc/greetd/dms-hypr.lua --cache-dir /var/cache/dms-greeter --remember-last-user false"
user = "greeter"
[initial_session]
command = "start-hyprland"
user = "desktop-account"
'''
    before = tomllib.loads(original)
    command = installer.themed_command(before["default_session"]["command"])
    changed = installer.replace_command(original, command)
    after = tomllib.loads(changed)
    assert after["terminal"] == before["terminal"]
    assert after["initial_session"] == before["initial_session"]
    assert after["default_session"]["user"] == "greeter"
    assert changed.startswith("# Keep local greeter")
    args = shlex.split(command)
    assert args[args.index("--") + 1:] == shlex.split(before["default_session"]["command"])[1:]
    assert installer.themed_command(command) == command
    assert installer.replace_command(changed, command) == changed
    for selector in ("--shell-dir /custom/ui", "--shell-dir=/custom/ui", "-c /custom/ui", "-c/custom/ui", "--path custom", "-p custom"):
        try:
            installer.themed_command(before["default_session"]["command"] + " " + selector)
        except ValueError:
            pass
        else:
            raise AssertionError("Accepted a custom UI that defeats the guarded fallback")
    for unsupported in ["/usr/bin/agreety", "/custom/local-login --foo"]:
        try:
            installer.themed_command(unsupported)
        except ValueError:
            pass
        else:
            raise AssertionError("Replaced an unrelated login manager")
    # TOML basic-string escaping must preserve literal shell syntax, not expand it.
    quoted = installer.replace_command(original, command + " --name 'with space $HOME'")
    assert tomllib.loads(quoted)["default_session"]["command"].endswith("--name 'with space $HOME'")
    with tempfile.TemporaryDirectory(prefix="greeter-install-check-") as directory:
        root = Path(directory)
        source = root / "source.py"
        source.write_text("# launcher\n")
        previous_mask = os.umask(0o077)
        try:
            target = root / "usr/local/libexec/launcher.py"
            installer.install_file(source, target)
        finally:
            os.umask(previous_mask)
        assert target.read_bytes() == source.read_bytes()
        assert target.stat().st_mode & 0o777 == 0o644
        for path in (root / "usr", root / "usr/local", target.parent):
            assert path.stat().st_mode & 0o777 == 0o755, path
        original_source = root / "old-launcher"
        original_source.write_text("preserve unrelated source")
        target.unlink()
        target.symlink_to(original_source)
        installer.install_file(source, target)
        assert not target.is_symlink() and original_source.read_text() == "preserve unrelated source"
    print("PASS: theme installation preserves compositor/session options, auto-login, comments and unrelated login managers; repeat install is stable")


if __name__ == "__main__":
    main()
