#!/usr/bin/env python3
"""Validate shared sources and exercise installation without live services."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import unquote, urlsplit


def check_sources(agent):
    """Check discovery/provenance coverage and maintained local file links."""
    skills = {path.parent.name: path for path in (agent / "skills").glob("*/SKILL.md")}
    registry = json.loads((agent / "skills/SOURCES.json").read_text())
    assert set(registry["skills"]) == set(skills), "Skill provenance coverage differs from installed sources"
    upstreams = {item["id"]: item for item in registry["upstreams"]}
    assert len(upstreams) == len(registry["upstreams"]), "Duplicate upstream IDs"
    for directory, path in skills.items():
        entry = registry["skills"][directory]
        match = re.search(r"^name:\s*(.+)$", path.read_text(), re.MULTILINE)
        assert match, f"Missing catalogue name: {path}"
        assert match[1].strip(' \"\'') == entry.get("catalogueName", directory), f"Catalogue alias differs: {path}"
        assert entry["origin"] in ("personal", "adapted", "unresolved"), f"Unknown origin: {directory}"
        if entry["origin"] == "adapted":
            upstream = upstreams[entry["upstream"]]
            assert directory in upstream["skills"], f"Upstream does not cover {directory}"
    for upstream in upstreams.values():
        for directory in upstream["skills"]:
            assert registry["skills"][directory].get("upstream") == upstream["id"], f"Inconsistent upstream: {directory}"
    for alias in ("GLOBAL.md", "PERSONAL.md", "LETTER.md"):
        path = agent / alias
        assert path.is_symlink() and path.resolve() == agent / "AGENTS.md", f"Not a root alias: {path}"

    maintained = [agent / name for name in ("AGENTS.md", "README.md", "philosophy.md",
                                            "fleet/README.md", "fleet/WORKFLOW.md")]
    maintained.extend((agent / "workflows").glob("*.md"))
    maintained.extend(skills.values())
    for path in maintained:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            link = urlsplit(target)
            if link.scheme or not link.path or link.path.startswith(("/", "~", "<", "{")):
                continue
            assert (path.parent / unquote(link.path)).exists(), f"Broken local link: {path}: {target}"


def main():
    source = Path(__file__).resolve().with_name("install-agent-kit.sh")
    agent_source = source.parent.parent / "agent"
    check_sources(agent_source)
    with tempfile.TemporaryDirectory(prefix="agent-kit-check-") as directory:
        root = Path(directory)
        # Missing provenance must fail even when installation would discover the skill.
        source_copy = root / "source check"
        shutil.copytree(agent_source, source_copy, symlinks=True)
        (source_copy / "skills/unregistered").mkdir()
        (source_copy / "skills/unregistered/SKILL.md").write_text("---\nname: unregistered\ndescription: Fixture\n---\n")
        try:
            check_sources(source_copy)
        except AssertionError as error:
            assert "provenance coverage" in str(error)
        else:
            raise AssertionError("Missing provenance was accepted")
        repo = root / "repo with spaces"
        home = root / "staged home"
        agent = repo / "agent"
        scripts = repo / "scripts"
        scripts.mkdir(parents=True)
        (agent / "cursor-rules").mkdir(parents=True)
        (agent / "skills" / "example").mkdir(parents=True)
        home.mkdir()
        shutil.copy2(source, scripts / source.name)
        (agent / "AGENTS.md").write_text("Root agent instructions\n")
        (agent / "GLOBAL.md").symlink_to("AGENTS.md")
        (agent / "PERSONAL.md").symlink_to("AGENTS.md")
        (agent / "LETTER.md").symlink_to("AGENTS.md")
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
        (home / ".config/opencode").mkdir(parents=True)
        (home / ".config/opencode/AGENTS.md").symlink_to(agent / "GLOBAL.md")
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

        def run(*arguments, expected=0):
            result = subprocess.run(
                ["bash", str(scripts / source.name), *arguments],
                env=env, capture_output=True, text=True,
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
        assert (home / "AGENTS.md").resolve() == agent / "AGENTS.md"
        assert (backup / ".config/opencode/AGENTS.md").readlink() == agent / "GLOBAL.md"
        assert (home / ".config/opencode/AGENTS.md").readlink() == agent / "AGENTS.md"
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
        (agent / "AGENTS.md").write_text("Updated shared instructions\n")
        for legacy in ("GLOBAL.md", "PERSONAL.md", "LETTER.md"):
            assert (agent / legacy).read_text() == "Updated shared instructions\n"
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
        assert (custom / "AGENTS.md").resolve() == agent / "AGENTS.md"
        run("--check")
    print("PASS: provenance coverage, catalogue aliases, local file links, dry run, backups, idempotency, migration, skill updates and readiness checks")


if __name__ == "__main__":
    main()
