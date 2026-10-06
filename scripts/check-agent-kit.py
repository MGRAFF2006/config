#!/usr/bin/env python3
"""Exercise installation in a temporary repo/home without model calls or services."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().with_name("install-agent-kit.sh")
    with tempfile.TemporaryDirectory(prefix="agent-kit-check-") as directory:
        root = Path(directory)
        repo = root / "repo with spaces"
        home = root / "staged home"
        agent = repo / "agent"
        scripts = repo / "scripts"
        scripts.mkdir(parents=True)
        (agent / "cursor-rules").mkdir(parents=True)
        (agent / "skills" / "example").mkdir(parents=True)
        home.mkdir()
        shutil.copy2(source, scripts / source.name)
        (agent / "GLOBAL.md").write_text("Personal instructions and letter\n")
        (agent / "PERSONAL.md").symlink_to("GLOBAL.md")
        (agent / "LETTER.md").symlink_to("GLOBAL.md")
        (agent / "cursor-rules/letter.mdc").symlink_to("../GLOBAL.md")
        (agent / "skills/example/SKILL.md").write_text(
            "---\nname: example\ndescription: Test fixture\n---\n"
        )
        # Fixtures prove that conflicting files/directories and broken links survive.
        (home / "AGENTS.md").write_text("Keep my existing instructions\n")
        (home / ".agents/skills/example").mkdir(parents=True)
        (home / ".agents/skills/example/custom.txt").write_text("Keep my skill\n")
        (home / ".codex").mkdir()
        (home / ".codex/AGENTS.md").symlink_to(root / "missing-old-target")
        (home / ".cursor/skills").mkdir(parents=True)
        (home / ".cursor/skills/example").symlink_to(agent / "skills/example")
        (home / ".cursor/skills/unrelated").mkdir()
        (home / ".cursor/skills/unrelated/keep.txt").write_text("untouched\n")

        (home / ".cursor/rules").mkdir()
        (home / ".cursor/rules/letter.mdc").symlink_to(agent / "cursor-rules/letter.mdc")
        (home / ".cursor/rules/personal-machines.mdc").symlink_to(agent / "PERSONAL.md")
        (home / ".cursor/rules/agent-kit.mdc").symlink_to(agent / "GLOBAL.md")
        (home / ".cursor/rules/unrelated.mdc").write_text("keep this rule\n")
        shutil.copytree(agent / "skills/example", home / ".codex/skills/example")
        (home / ".codex/skills/.system").mkdir()
        (home / ".codex/skills/.system/keep.txt").write_text("managed by Codex\n")
        (home / ".claude/skills/synced").mkdir(parents=True)
        (home / ".claude/skills/synced/keep.txt").write_text("machine-local\n")

        binaries = root / "bin"
        binaries.mkdir()
        for tool in ("git", "ssh", "rsync", "tmux", "tailscale", "syncthing", "codex", "systemctl"):
            path = binaries / tool
            path.write_text("#!/bin/sh\nexit 0\n")
            path.chmod(0o755)
        env = dict(os.environ, AGENT_KIT_HOME=str(home), PATH=f"{binaries}:{os.environ['PATH']}")
        env.pop("CODEX_HOME", None)
        env.pop("XDG_CONFIG_HOME", None)

        def run(*arguments, expected=0, cwd=None):
            result = subprocess.run(
                ["bash", str(scripts / source.name), *arguments],
                env=env, capture_output=True, text=True, cwd=cwd,
            )
            assert result.returncode == expected, result.stdout + result.stderr
            return result

        run("--dry-run")
        assert (home / "AGENTS.md").read_text() == "Keep my existing instructions\n"
        assert not (home / ".local").exists()
        assert (agent / "cursor-rules/letter.mdc").is_symlink()
        run("unknown", expected=2)
        run("--check", expected=1)
        run()
        backups = list((home / ".local/share/agent-kit-backups").iterdir())
        assert len(backups) == 1
        backup = backups[0]
        assert (backup / "AGENTS.md").read_text() == "Keep my existing instructions\n"
        assert (backup / ".agents/skills/example/custom.txt").read_text() == "Keep my skill\n"
        assert (backup / ".codex/AGENTS.md").readlink() == root / "missing-old-target"
        assert (home / "AGENTS.md").resolve() == agent / "GLOBAL.md"
        assert (home / ".agents/skills").is_symlink()
        assert (home / ".agents/skills").resolve() == agent / "skills"
        assert (home / ".claude/skills/example").resolve() == agent / "skills/example"
        assert not (home / ".claude/skills").is_symlink()
        assert (home / ".claude/skills/synced/keep.txt").read_text() == "machine-local\n"
        assert (backup / ".codex/skills/example/SKILL.md").read_text() == (agent / "skills/example/SKILL.md").read_text()
        assert (home / ".codex/skills/.system/keep.txt").read_text() == "managed by Codex\n"
        assert not (home / ".cursor/rules/letter.mdc").is_symlink()
        assert not (home / ".cursor/rules/personal-machines.mdc").is_symlink()
        assert not (home / ".cursor/rules/agent-kit.mdc").exists()
        assert (backup / ".cursor/rules/agent-kit.mdc").is_symlink()
        assert (home / ".cursor/rules/unrelated.mdc").read_text() == "keep this rule\n"
        assert not (home / ".cursor/skills/example").is_symlink()
        assert (home / ".cursor/skills/unrelated/keep.txt").read_text() == "untouched\n"
        run()
        assert list((home / ".local/share/agent-kit-backups").iterdir()) == backups
        (agent / "GLOBAL.md").write_text("Updated shared instructions\n")
        for target in ["AGENTS.md", ".codex/AGENTS.md", ".config/opencode/AGENTS.md",
                       ".claude/CLAUDE.md"]:
            assert (home / target).read_text() == "Updated shared instructions\n"
        run("--check")
        (agent / "skills/new-skill").mkdir()
        (agent / "skills/new-skill/SKILL.md").write_text("new workflow\n")
        assert (home / ".agents/skills/new-skill/SKILL.md").read_text() == "new workflow\n"
        run("--check", expected=1)  # Claude still needs its new per-skill link.
        run()
        run("--check")
        (home / ".claude/skills/example").unlink()
        run("--check", expected=1)
        # A custom Codex home is read, not overwritten as an environment setting.
        custom = root / "alternate codex"
        env["CODEX_HOME"] = str(custom)
        run()
        assert (custom / "AGENTS.md").resolve() == agent / "GLOBAL.md"
        run("--check")
        # Shared parent links must never move a source into a home backup.
        for relative, shared, aliased in ((".claude/skills", "agent/skills", False),
                                          (".codex/skills", "agent/skills", False),
                                          (".config/opencode", "agent", False),
                                          (".local/share/agent-kit-backups", "agent", False),
                                          (".claude/skills", "agent/skills", True)):
            fixture = root / (relative.replace("/", "-") + ("-aliased" if aliased else ""))
            shared_repo = fixture / "repo"
            isolated_home = fixture / "home"
            (shared_repo / "scripts").mkdir(parents=True)
            shutil.copy2(source, shared_repo / "scripts" / source.name)
            shutil.copytree(agent, shared_repo / "agent", symlinks=True)
            destination = isolated_home / relative
            destination.parent.mkdir(parents=True)
            destination.symlink_to(shared_repo / shared, target_is_directory=True)
            if relative == ".config/opencode":
                (shared_repo / "agent/AGENTS.md").write_text("Keep shared instructions\n")
            if relative == ".local/share/agent-kit-backups":
                (isolated_home / "AGENTS.md").write_text("Keep local instructions\n")
            checkout = shared_repo
            if aliased:
                checkout = fixture / "linked checkout"
                checkout.symlink_to(shared_repo, target_is_directory=True)
            result = subprocess.run(
                ["bash", str(checkout / "scripts" / source.name)],
                env=dict(env, AGENT_KIT_HOME=str(isolated_home),
                         CODEX_HOME=str(isolated_home / ".codex"),
                         XDG_CONFIG_HOME=str(isolated_home / ".config")),
                capture_output=True, text=True,
            )
            assert result.returncode == 1, result.stdout + result.stderr
            assert "Destination parent points into shared repo" in result.stderr
            assert (shared_repo / "agent/skills/example/SKILL.md").read_text() == (agent / "skills/example/SKILL.md").read_text()
            assert (shared_repo / "agent/GLOBAL.md").read_text() == (agent / "GLOBAL.md").read_text()
            if relative == ".config/opencode":
                assert (shared_repo / "agent/AGENTS.md").read_text() == "Keep shared instructions\n"
            if relative == ".local/share/agent-kit-backups":
                assert (isolated_home / "AGENTS.md").read_text() == "Keep local instructions\n"
                assert sorted(path.name for path in (shared_repo / "agent").iterdir()) == sorted(path.name for path in agent.iterdir())
        # External relative roots cannot escape the printed backup directory.
        deep = root / "a/b/c/d/e/f/g/h"
        deep.mkdir(parents=True)
        relative_codex = "../" * 7 + "repo with spaces/agent/local"
        external = (deep / relative_codex).resolve()
        external.mkdir(parents=True)
        (external / "AGENTS.md").write_text("Keep external instructions\n")
        env["CODEX_HOME"] = relative_codex
        run(cwd=deep)
        assert not (agent / "local").exists()
        assert (external / "AGENTS.md").resolve() == agent / "GLOBAL.md"
        saved = home / ".local/share/agent-kit-backups"
        assert any(path.read_text() == "Keep external instructions\n"
                   for path in saved.glob("*/external/**/AGENTS.md"))
    print("PASS: dry run, backups, idempotency, shared instruction and skill updates, migration, local tool state, and readiness checks")


if __name__ == "__main__":
    main()
