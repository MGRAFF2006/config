#!/usr/bin/env python3
"""Install the DMS login-screen appearance without changing authentication."""

import argparse
from datetime import datetime
import grp
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = Path("/usr/local/libexec/config-dms-greeter.py")
UI = Path("/usr/local/share/config-dms-greeter-ui")


def themed_command(command):
    """Preserve every greeter option, including the compositor and cache path."""
    argv = shlex.split(command)
    if len(argv) > 1 and argv[1] == str(WRAPPER):
        argv = ["/usr/bin/dms-greeter", *argv[argv.index("--") + 1:]]
    if not argv or Path(argv[0]).name != "dms-greeter":
        raise ValueError("The active greetd command is not the managed DMS greeter")
    for argument in argv[1:]:
        if any(argument == flag or argument.startswith(flag + "=") for flag in ("--shell-dir", "--path")) or (argument.startswith(("-c", "-p")) and not argument.startswith("--")):
            raise ValueError("Remove the custom greeter UI selector before installing the guarded renderer")
    return shlex.join(["/usr/bin/python3", str(WRAPPER), "--output", str(UI), "--launch", "--", *argv[1:]])


def replace_command(content, command):
    before = tomllib.loads(content)
    section = re.search(r"(?ms)^\[default_session\][^\n]*\n.*?(?=^\[|\Z)", content)
    if not section:
        raise ValueError("Missing greetd default_session section")
    block, count = re.subn(r"(?m)^command\s*=.*$", lambda _: "command = " + json.dumps(command), section[0])
    if count != 1:
        raise ValueError("Expected one single-line greeter command")
    updated = content[:section.start()] + block + content[section.end():]
    expected = dict(before)
    expected["default_session"] = dict(before["default_session"], command=command)
    if tomllib.loads(updated) != expected:
        raise ValueError("Refusing to change other greetd settings")
    return updated


def backup_file(path, backup):
    target = backup / path.relative_to("/")
    if not path.exists() and not path.is_symlink():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        target.symlink_to(os.readlink(path))
    elif path.is_dir():
        shutil.copytree(path, target, symlinks=True)
    else:
        shutil.copy2(path, target)


def system_directory(path):
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir()
        directory.chmod(0o755)


def install_file(source, target, mode=0o644):
    system_directory(target.parent)
    # Replacing a symlink must never write back into its old source.
    fd, name = tempfile.mkstemp(dir=target.parent, prefix="." + target.name)
    try:
        os.close(fd)
        shutil.copyfile(source, name)
        os.chmod(name, mode)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Back up and install; never restart greetd")
    parser.add_argument("--user", help="Desktop account (defaults to the invoking user)")
    parser.add_argument("--source-dir", type=Path, help="Pristine extracted greeter UI")
    args = parser.parse_args()
    username = args.user or os.environ.get("SUDO_USER") or pwd.getpwuid(os.getuid()).pw_name
    account = pwd.getpwnam(username)
    if account.pw_uid == 0:
        parser.error("Choose the desktop account with --user")
    home = Path(account.pw_dir)
    config = Path("/etc/greetd/config.toml")
    content = config.read_text()
    command = themed_command(tomllib.loads(content)["default_session"]["command"])
    updated = replace_command(content, command)
    # Reject another compositor/cache before any mutations. This installer is
    # intentionally limited to this repository's managed Hyprland greeter.
    native_args = shlex.split(command)[shlex.split(command).index("--") + 1:]
    for option, value in (("--command", "hyprland"), ("-C", "/etc/greetd/dms-hypr.lua")):
        if option not in native_args or native_args[native_args.index(option) + 1] != value:
            parser.error("Expected the managed Hyprland greeter; configure its compositor separately")
    cache = Path(native_args[native_args.index("--cache-dir") + 1]) if "--cache-dir" in native_args else Path("/var/cache/dms-greeter")
    if cache != Path("/var/cache/dms-greeter"):
        parser.error("This install flow requires the default DMS greeter cache")
    for source in (home / ".config/dms/settings.json", home / ".local/state/dms/session.json", home / ".cache/dms/dms-colors.json"):
        json.loads(source.read_text())
    print(f"Theme account: {username}; greeter: {config}; no display-manager restart", flush=True)
    if not args.apply:
        print("Use --apply to install theme sync, the guarded renderer, and compositor effects.")
        return
    if grp.getgrnam("greeter").gr_gid not in os.getgrouplist(username, account.pw_gid):
        parser.error("The desktop account must already be a member of the greeter group")
    for program in ("patch", "getfacl", "setfacl", "dms-greeter"):
        if not shutil.which(program):
            parser.error(f"Missing required program: {program}")
    subprocess.run([sys.executable, "-c", "from gi.repository import Gio, GLib"], check=True)
    if os.geteuid() != 0:
        os.execvp("sudo", ["sudo", sys.executable, str(Path(__file__).resolve()), *os.sys.argv[1:], "--user", username])

    backup_root = Path("/var/backups/config-dms-greeter-theme")
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y-%m-%d_%H-%M-%S-"), dir=backup_root))
    paths = [config, Path("/etc/greetd/dms-hypr.lua"), Path("/etc/greetd/dms-appearance.lua"), WRAPPER, UI, cache / "users" / username]
    paths += [cache / name for name in ("settings.json", "session.json", "colors.json")]
    for path in paths:
        backup_file(path, backup)
    acl_paths = [home, home / ".config", home / ".local", home / ".local/state", home / ".cache"]
    acl_paths += [home / part / "dms" for part in (".config", ".local/state", ".cache")]
    with (backup / "permissions.acl").open("w") as stream:
        subprocess.run(["getfacl", "-p", *map(str, acl_paths[:5])], check=True, stdout=stream)
        subprocess.run(["getfacl", "-R", "-p", *map(str, acl_paths[5:])], check=True, stdout=stream)
    print(f"Backup: {backup}", flush=True)
    staged = backup / "staged-ui"
    prepare = ["python3", str(ROOT / "scripts/configure-dms-greeter-ui.py"), "--apply", "--output", str(staged)]
    if args.source_dir:
        prepare += ["--source-dir", str(args.source_dir)]
    subprocess.run(prepare, check=True)
    # Stage and validate everything before replacing the active renderer.
    system_directory(UI.parent)
    if UI.exists():
        shutil.rmtree(UI)
    shutil.copytree(staged, UI)
    for path in [UI, *UI.rglob("*")]:
        if not path.is_symlink():
            path.chmod(0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644)
    install_file(ROOT / "scripts/configure-dms-greeter-ui.py", WRAPPER)
    appearance = home / ".config/hypr/dms/expressive.lua"
    install_file(appearance if appearance.is_file() else ROOT / "home/.config/hypr/dms/expressive.lua", Path("/etc/greetd/dms-appearance.lua"))
    install_file(ROOT / "system/greetd/dms-hypr.lua", Path("/etc/greetd/dms-hypr.lua"))
    temporary = backup / "config.toml.new"
    temporary.write_text(updated)
    install_file(temporary, config)
    for name, source in (("settings.json", home / ".config/dms/settings.json"), ("session.json", home / ".local/state/dms/session.json"), ("colors.json", home / ".cache/dms/dms-colors.json")):
        link = cache / name
        link.unlink(missing_ok=True)
        link.symlink_to(source)
    user_env = ["env", f"HOME={home}", f"XDG_CONFIG_HOME={home}/.config", f"XDG_STATE_HOME={home}/.local/state", f"XDG_CACHE_HOME={home}/.cache", f"XDG_RUNTIME_DIR=/run/user/{account.pw_uid}", f"DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/{account.pw_uid}/bus"]
    def as_user(*argv):
        subprocess.run(["runuser", "-u", username, "--", *user_env, *argv], check=True)
    links = [".config/systemd/user/dms-greeter-settings-permissions." + suffix for suffix in ("service", "path")]
    links.append(".local/bin/dms-greeter-theme-watch")
    for relative in links:
        target = home / relative
        backup_file(target, backup)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        target.symlink_to(ROOT / "home" / relative)
        os.lchown(target, account.pw_uid, account.pw_gid)
    as_user("systemctl", "--user", "daemon-reload")
    as_user("systemctl", "--user", "reset-failed", "dms-greeter-settings-permissions.service", "dms-greeter-settings-permissions.path")
    as_user("systemctl", "--user", "enable", "dms-greeter-settings-permissions.service")
    as_user("systemctl", "--user", "restart", "dms-greeter-settings-permissions.service")
    as_user("systemctl", "--user", "enable", "dms-greeter-settings-permissions.path")
    as_user("systemctl", "--user", "restart", "dms-greeter-settings-permissions.path")
    as_user("dms-greeter", "status")
    print("Installed. The next login screen uses this theme; greetd was not restarted and PAM was not changed.")


if __name__ == "__main__":
    main()
