#!/usr/bin/env python3
"""Add managed SSH includes while retaining local keys and host settings."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("machine", choices=("laptop", "desktop", "homelab-dev"))
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", dest="mode", action="store_const", const="--dry-run")
    modes.add_argument("--check", dest="mode", action="store_const", const="--check")
    parser.set_defaults(mode="install")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    home = Path(os.environ.get("CONFIG_LINK_HOME", Path.home()))
    config = home / ".ssh/config"
    fragments = [repo / "ssh/workstations.conf", repo / "ssh/homelab.conf"]
    if args.machine == "homelab-dev":
        fragments.append(repo / "ssh/homelab-dev-github.conf")
    for fragment in fragments:
        if not fragment.is_file():
            raise SystemExit(f"Missing SSH fragment: {fragment}")
    original = config.read_text() if config.exists() else ""
    # Do not replace a linked SSH source: it may belong to another managed tree.
    if config.is_symlink():
        raise SystemExit(f"SSH config is a symlink; manage its Include directives in its source: {config}")
    includes = [f'Include "{str(path).replace(chr(34), chr(92) + chr(34))}"' for path in fragments]
    existing = set()
    for line in original.splitlines():
        tokens = shlex.split(line, comments=True)
        if tokens and tokens[0].lower() == "include":
            existing.update(os.path.expanduser(token) for token in tokens[1:])
    missing = [line for line, path in zip(includes, fragments) if str(path) not in existing]
    if not missing:
        return
    if args.mode == "--check":
        raise SystemExit(f"Missing managed SSH includes in {config}")
    if args.mode == "--dry-run":
        print(f"ADD managed SSH includes to {config} (retain existing settings; back up)")
        return
    config.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix="config-", dir=config.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w") as stream:
            # Reset Host scope after included files before the old global settings.
            stream.write("\n".join(missing) + "\nHost *\n" + original)
        for host in ("desktop", "homelab-dev"):
            subprocess.run(["ssh", "-T", "-F", str(temporary), "-G", host], check=True, stdout=subprocess.DEVNULL)
        if config.exists():
            backup_dir = home / ".local/share/config-link-backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=backup_dir)) / ".ssh/config"
            backup.parent.mkdir()
            shutil.copy2(config, backup)
            print(f"BACKUP {config} -> {backup}")
        temporary.replace(config)
        print(f"Configured SSH includes: {config}")
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
