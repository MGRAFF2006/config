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
        for tool in ("git", "ssh", "rsync", "tmux", "tailscale", "syncthing", "systemctl"):
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
        env.pop("CODEX_HOME")
        # Codex may share Claude's root. The new Claude skill link is then also
        # the "legacy Codex" path; retiring it would back the same path up twice,
        # and the second move would land inside the first backup's local target.
        shared_home = root / "shared skill root home"
        local_skill = root / "local example skill"
        local_skill.mkdir()
        (local_skill / "example").write_text("Keep my local file\n")
        (shared_home / ".claude/skills").mkdir(parents=True)
        (shared_home / ".claude/skills/example").symlink_to(local_skill, target_is_directory=True)
        env["AGENT_KIT_HOME"] = str(shared_home)
        env["CODEX_HOME"] = str(shared_home / ".claude")
        run()
        assert not (local_skill / "example").is_symlink(), "A second backup overwrote a local file"
        assert (local_skill / "example").read_text() == "Keep my local file\n"
        assert (shared_home / ".claude/skills/example").readlink() == agent / "skills/example"
        saved_runs = list((shared_home / ".local/share/agent-kit-backups").iterdir())
        assert len(saved_runs) == 1
        assert (saved_runs[0] / ".claude/skills/example").readlink() == local_skill
        run()
        run("--check")
        assert list((shared_home / ".local/share/agent-kit-backups").iterdir()) == saved_runs
        env["AGENT_KIT_HOME"] = str(home)
        env.pop("CODEX_HOME")
        # A historical whole-root link must never turn source skills into backups
        # or self-referential links. Exercise both roots and a second installation.
        for tool in (".codex", ".claude"):
            alias_home = root / f"{tool[1:]} legacy home"
            (alias_home / tool).mkdir(parents=True)
            skill_root = alias_home / tool / "skills"
            skill_root.symlink_to(agent / "skills", target_is_directory=True)
            env["AGENT_KIT_HOME"] = str(alias_home)
            original = (agent / "skills/example/SKILL.md").read_bytes()
            run("--dry-run")
            assert skill_root.is_symlink()
            run()
            assert not skill_root.is_symlink()
            assert (agent / "skills/example").is_dir() and not (agent / "skills/example").is_symlink()
            assert (agent / "skills/example/SKILL.md").read_bytes() == original
            old_roots = list((alias_home / ".local/share/agent-kit-backups").glob(f"*/{tool}/skills"))
            assert len(old_roots) == 1 and old_roots[0].is_symlink()
            run()
            run("--check")
            assert (agent / "skills/example/SKILL.md").read_bytes() == original
        # An unexpected ancestor alias is rejected instead of writing into source.
        unsafe_home = root / "unsafe ancestor home"
        unsafe_home.mkdir()
        (unsafe_home / ".claude").symlink_to(agent, target_is_directory=True)
        env["AGENT_KIT_HOME"] = str(unsafe_home)
        original_root = (agent / "AGENTS.md").read_bytes()
        result = run(expected=1)
        assert "inside the source repo" in result.stderr
        assert (agent / "AGENTS.md").read_bytes() == original_root
        # A backup directory linked into the checkout must not receive local files.
        linked_backups = root / "linked backups home"
        (linked_backups / ".local/share").mkdir(parents=True)
        (linked_backups / ".local/share/agent-kit-backups").symlink_to(agent, target_is_directory=True)
        (linked_backups / "AGENTS.md").write_text("Keep local instructions\n")
        env["AGENT_KIT_HOME"] = str(linked_backups)
        source_entries = sorted(path.name for path in agent.iterdir())
        result = run(expected=1)
        assert "symlinked backup directory" in result.stderr
        assert sorted(path.name for path in agent.iterdir()) == source_entries
        assert (linked_backups / "AGENTS.md").read_text() == "Keep local instructions\n"
        # A relative Codex root outside the home is backed up inside the backup directory.
        env["AGENT_KIT_HOME"] = str(home)
        deep = root / "a/b/c"
        deep.mkdir(parents=True)
        external = root / "relative codex"
        external.mkdir()
        (external / "AGENTS.md").write_text("Keep external instructions\n")
        env["CODEX_HOME"] = "../../../relative codex"
        run(cwd=deep)
        assert (external / "AGENTS.md").resolve() == agent / "AGENTS.md"
        saved = home / ".local/share/agent-kit-backups"
        kept = [path for path in saved.glob("*/**/AGENTS.md")
                if not path.is_symlink() and path.read_text() == "Keep external instructions\n"]
        assert len(kept) == 1 and kept[0].resolve().is_relative_to(saved.resolve())
        assert not any(path.name == "external.." for path in root.rglob("external.."))
        # A root through a symlink and `..` follows the filesystem, not lexical
        # normalization: aliases/current/.. is intended/, not aliases/.
        def saved_texts(base):
            return sorted(path.read_text() for path in base.glob(".local/share/agent-kit-backups/*/**/AGENTS.md")
                          if path.is_file() and not path.is_symlink())
        (root / "intended/profile").mkdir(parents=True)
        (root / "intended/config").mkdir()
        (root / "aliases").mkdir()
        (root / "aliases/current").symlink_to(root / "intended/profile", target_is_directory=True)
        (root / "aliases/config").mkdir()
        (root / "aliases/config/AGENTS.md").write_text("Unrelated file\n")
        (root / "intended/config/AGENTS.md").write_text("Old intended file\n")
        env["CODEX_HOME"] = str(root / "aliases/current/../config")
        run()
        assert (root / "intended/config/AGENTS.md").resolve() == agent / "AGENTS.md"
        assert (root / "aliases/config/AGENTS.md").read_text() == "Unrelated file\n"
        assert "Old intended file\n" in saved_texts(home)
        # Two live files whose backup names coincide must both be kept. Here the
        # home itself is aliases/config, the lexical spelling of the Codex root.
        (root / "intended/config/AGENTS.md").unlink()
        (root / "intended/config/AGENTS.md").write_text("Old codex file\n")
        (root / "aliases/config/AGENTS.md").write_text("Old home file\n")
        env["AGENT_KIT_HOME"] = str(root / "aliases/config")
        run()
        assert (root / "aliases/config/AGENTS.md").resolve() == agent / "AGENTS.md"
        assert (root / "intended/config/AGENTS.md").resolve() == agent / "AGENTS.md"
        assert saved_texts(root / "aliases/config") == ["Old codex file\n", "Old home file\n"]
        # A legacy skill-root link archived earlier in the run must not become
        # the parent of a later backup and redirect it into the checkout.
        skill_home = root / "skill alias home"
        (skill_home / ".claude").mkdir(parents=True)
        (skill_home / ".claude/skills").symlink_to(agent / "skills", target_is_directory=True)
        (skill_home / "current").symlink_to(root / "intended/profile", target_is_directory=True)
        (root / "intended/.claude/skills").mkdir(parents=True)
        (root / "intended/.claude/skills/AGENTS.md").write_text("Old skill-path codex file\n")
        (root / "out").mkdir()
        env["AGENT_KIT_HOME"] = str(skill_home)
        env["CODEX_HOME"] = str(root / "out/../skill alias home/current/../.claude/skills")
        source_entries = sorted(path.name for path in (agent / "skills").iterdir())
        run()
        assert sorted(path.name for path in (agent / "skills").iterdir()) == source_entries
        assert "Old skill-path codex file\n" in saved_texts(skill_home)
        env["AGENT_KIT_HOME"] = str(home)
        # Unusual roots are refused before any change, in preview and install.
        def snapshot(*bases):
            state = {}
            for base in bases:
                for path in [base, *base.rglob("*")]:
                    state[path] = (os.readlink(path) if path.is_symlink()
                                   else path.read_bytes() if path.is_file() else "directory")
            return state

        def refused(message, *bases, script=scripts / source.name):
            before = snapshot(*bases)
            for arguments in (["--dry-run"], []):
                result = subprocess.run(["bash", str(script), *arguments],
                                        env=env, capture_output=True, text=True)
                assert result.returncode == 1, result.stdout + result.stderr
                assert message in result.stderr, result.stderr
                assert snapshot(*bases) == before, f"Refused run changed files: {message}"

        # A backup directory reached through a link can change during the run:
        # here ~/.agents/skills is replaced with a link into the checkout, so
        # later backups would follow it into agent/skills.
        for linked in (".local/share/agent-kit-backups", ".local/share"):
            moving = root / f"moving backups {linked.count('/')}"
            local_skills = moving / "local skills"
            local_skills.mkdir(parents=True)
            (moving / ".agents").mkdir()
            (moving / ".agents/skills").symlink_to(local_skills, target_is_directory=True)
            (moving / linked).parent.mkdir(parents=True, exist_ok=True)
            (moving / linked).symlink_to(moving / ".agents/skills", target_is_directory=True)
            (moving / "AGENTS.md").write_text("Keep local instructions\n")
            (moving / ".claude/skills/example").mkdir(parents=True)
            (moving / ".claude/skills/example/LOCAL.md").write_text("Keep local skill\n")
            env["AGENT_KIT_HOME"] = str(moving)
            refused("symlinked backup directory", moving, agent)
        # Command substitutions drop trailing newlines, so a root ending in one
        # can be checked under a sibling's name. A Codex root `codex\n` that
        # links to agent/ would let the guard check `codex` instead.
        env["AGENT_KIT_HOME"] = str(home)
        (root / "codex\n").symlink_to(agent, target_is_directory=True)
        env["CODEX_HOME"] = str(root / "codex\n")
        refused("newline", home, agent)
        env.pop("CODEX_HOME")
        newline_home = root / "newline home\n"
        newline_home.mkdir()
        (root / "newline home").mkdir()
        env["AGENT_KIT_HOME"] = str(newline_home)
        refused("newline", newline_home, root / "newline home")
        env["AGENT_KIT_HOME"] = str(home)
        # A checkout ending in a newline would take sources from a sibling checkout.
        newline_repo = root / "repo with spaces\n"
        shutil.copytree(repo, newline_repo, symlinks=True)
        refused("newline", home, repo, newline_repo, script=newline_repo / "scripts" / source.name)
    print("PASS: provenance coverage, catalogue aliases, local file links, dry run, backups, idempotency, migration, skill updates, linked backup and relative-root safety, unusual-root refusal, and readiness checks")


if __name__ == "__main__":
    main()
