#!/usr/bin/env python3
"""Exercise actual launcher result rows with synthetic data in a private, throwaway desktop.

Stages the guarded UI override from a private copy of the DMS UI into a
temporary directory, checks that the launch guard covers every patched file,
then runs scripts/fixtures/launcher-text-bounds.qml against the staged
components. Qt's offscreen platform cannot load DMS's PanelWindow types, so the
fixture runs on a private rootful Xwayland inside a headless KWin. Both run in
bubblewrap with a read-only root, throwaway HOME and /tmp, no network and a
private D-Bus; nothing reaches the running desktop, its settings or services.
--self-test checks the private copy and guard probes without a desktop or DMS.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from unittest.mock import patch

SESSION = """mkdir -p -m 1777 /tmp/.X11-unix
Xwayland :7 -geometry 1440x900 -shm -nolisten tcp &
for _ in $(seq 100); do [ -S /tmp/.X11-unix/X7 ] && break; sleep 0.1; done
DISPLAY=:7 QT_QPA_PLATFORM=xcb exec qs -p "$1"
"""


def load_configure():
    spec = importlib.util.spec_from_file_location("ui_override", Path(__file__).with_name("configure-dms-smooth-sliders.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def running_ui_source():
    """The running shell's extracted UI, found the same way as the configure helper."""
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    return Path((runtime / "dms.path").read_text().strip())


def check_launch_guard(module, staged, work):
    """The staged UI launches only while its version and every patched renderer match."""
    manifest = json.loads((staged / "smooth-sliders.json").read_text())
    output = work / "guard"
    output.mkdir()
    (output / "active.json").write_text(json.dumps({"target": str(staged)}))

    class Launched(Exception):
        pass

    def launch_arguments(version=manifest["version"]):
        with patch.object(module.os, "execvp", side_effect=Launched) as execute, \
                patch.object(module.subprocess, "check_output", return_value=f"dms {version}\n"):
            try:
                module.launch(output)
            except Launched:
                pass
        return execute.call_args.args[1]

    assert launch_arguments() == ["dms", "-c", str(staged), "run", "-d"]
    for name in manifest["files_sha256"]:
        target = staged / name
        # The probe below writes; only ever into regular files of the private tree.
        if target.is_symlink() or not target.resolve().is_relative_to(work.resolve()):
            raise AssertionError(f"Refusing to probe {target}: it is not a private regular file")
        original = target.read_bytes()
        target.write_bytes(original + b"\n// altered\n")
        assert launch_arguments() == ["dms", "run", "-d"]
        target.write_bytes(original)
    assert launch_arguments("v9.0.0") == ["dms", "run", "-d"]


def prepare_ui(module, source, work, unpatched):
    """Return a private UI tree: pristine for --unpatched, otherwise staged and guard-checked."""
    if unpatched and (source / "smooth-sliders.json").exists():
        raise SystemExit(f"{source} is a staged override, not pristine input; pass --source-dir PRISTINE_DMS_UI with --unpatched.")
    # stage() reuses an intact active stage whose extraction was cleared on
    # reboot. A private copy keeps the tamper checks away from the live stage,
    # and the sandbox cannot see /run/user or HOME anyway. Symlinks are copied
    # as their targets so no probe write can follow one out of the copy.
    private = work / "input"
    shutil.copytree(source, private, symlinks=False, ignore_dangling_symlinks=True)
    if unpatched:
        return private
    staged = module.stage(private, work / "staged")
    assert module.stage(staged, work / "staged") == staged
    check_launch_guard(module, staged, work)
    return staged


def run_isolated(work, ui, fixture_name, env_extra):
    """Run a fixture against the UI tree in a private headless desktop; return its logs."""
    for tool in ("bwrap", "dbus-run-session", "kwin_wayland", "Xwayland", "qs"):
        if shutil.which(tool) is None:
            raise SystemExit(f"{tool} is required for the isolated DMS UI check")
    fixture = work / "fixture"
    fixture.mkdir()
    for entry in ui.iterdir():
        if entry.is_dir():
            (fixture / entry.name).symlink_to(entry, target_is_directory=True)
    (fixture / "shell.qml").write_text(Path(__file__).with_name("fixtures").joinpath(fixture_name).read_text())
    (work / "session.sh").write_text(SESSION)
    (work / "runtime").mkdir(mode=0o700)
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8", "TMPDIR": "/tmp",
        "XDG_RUNTIME_DIR": str(work / "runtime"), "XDG_CURRENT_DESKTOP": "KDE",
        # Software rendering: no GPU device is exposed inside the sandbox.
        "LIBGL_ALWAYS_SOFTWARE": "1", "__EGL_VENDOR_LIBRARY_FILENAMES": "/usr/share/glvnd/egl_vendor.d/50_mesa.json",
        "QT_QUICK_BACKEND": "software", "QT_QPA_PLATFORMTHEME": "", "QT_NO_XDG_DESKTOP_PORTAL": "1",
        **env_extra,
    }
    command = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
               "--tmpfs", "/tmp", "--tmpfs", "/run/user", "--tmpfs", str(Path.home()),
               "--bind", str(work), str(work), "--chdir", str(work),
               "--unshare-pid", "--unshare-net", "--die-with-parent", "--clearenv"]
    for key, value in env.items():
        command += ["--setenv", key, value]
    command += ["dbus-run-session", "--", "kwin_wayland", "--virtual", "--no-lockscreen", "--no-global-shortcuts",
                "--no-kactivities", "--socket", "check-wayland", "--width", "1440", "--height", "900",
                # KWin splits this argument into words, so a TMPDIR with spaces
                # would split its paths. --chdir makes these names relative to work.
                "--exit-with-session", "sh session.sh fixture"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired as error:
        raise AssertionError((error.stdout or b"").decode() + (error.stderr or b"").decode()) from error
    return result.stdout + result.stderr


def self_test():
    """Regression without a desktop: guard probes never write outside the private copy."""
    module = load_configure()
    with tempfile.TemporaryDirectory(prefix="launcher-check-self-test-") as directory:
        root = Path(directory)
        runtime = root / "runtime"
        runtime.mkdir()
        (runtime / "dms.path").write_text(str(root / "stage") + "\n")
        with patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(runtime)}):
            assert running_ui_source() == root / "stage", "dms.path ignored XDG_RUNTIME_DIR"
        # For each supported version: an intact active stage whose extraction
        # was cleared on reboot and whose every patched renderer (including
        # 2.1.2's ClipboardEntry.qml) links to an identical file outside it.
        binary = root / "dms"
        binary.write_text("reviewed binary")
        for version, files in module.VERSION_FILES.items():
            stage, outside = root / version / "stage", root / version / "outside"
            outside.mkdir(parents=True)
            external = {}
            for path in files:
                (stage / path.parent).mkdir(parents=True, exist_ok=True)
                external[path] = outside / str(path).replace("/", "_")
                external[path].write_text(f"reviewed {path}\n")
                (stage / path).symlink_to(external[path])
            (stage / "VERSION").write_text(version + "\n")
            manifest = {"version": version, "source": str(root / version / "extraction-cleared-on-reboot"),
                        "patch_sha256": module.patch_digest(version), "files_sha256": module.patched_files(stage, version),
                        "dms_binary_sha256": module.digest(binary)}
            (stage / "smooth-sliders.json").write_text(json.dumps(manifest))
            expected = {path: target.read_bytes() for path, target in external.items()}
            launch = module.launch

            def watched_launch(output):
                for path, target in external.items():
                    assert target.read_bytes() == expected[path], f"launch-guard probe wrote through a symlink outside the private copy ({path})"
                return launch(output)

            work = root / version / "work"
            work.mkdir()
            with patch.object(module.shutil, "which", return_value=str(binary)), patch.object(module, "launch", watched_launch):
                staged = prepare_ui(module, stage, work, unpatched=False)
            assert staged.resolve().is_relative_to(work.resolve())
            for path, target in external.items():
                assert (stage / path).is_symlink() and target.read_bytes() == expected[path]
        # A TMPDIR with spaces must still start the fixture inside the private desktop.
        work = root / "tmp with spaces"
        work.mkdir()
        (work / "ui" / "Modals").mkdir(parents=True)
        with patch.object(shutil, "which", return_value="/usr/bin/tool"), \
                patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            run_isolated(work, work / "ui", "launcher-text-bounds.qml", {})
        command = run.call_args.args[0]
        session = shlex.split(command[command.index("--exit-with-session") + 1])
        directory = Path(command[command.index("--chdir") + 1])
        assert session[0] == "sh" and (directory / session[1]).is_file() and (directory / session[1]).read_text() == SESSION, session
        assert (directory / session[2] / "shell.qml").is_file(), session
    print(f"PASS: dms.path honors XDG_RUNTIME_DIR; guard probes stay in the private copy when an input stage links outside it ({', '.join(module.VERSION_FILES)}); session starts with spaces in TMPDIR")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-dir", type=Path, help="Pristine DMS UI; defaults to the running shell's dms.path")
    parser.add_argument("--unpatched", action="store_true", help="Reproduce the failure against pristine components")
    parser.add_argument("--evidence", type=Path, help="Save the rendered fixture as a PNG")
    parser.add_argument("--self-test", action="store_true", help="Check staging isolation only; needs no desktop or DMS")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    module = load_configure()
    source = args.source_dir or running_ui_source()
    source = source.resolve(strict=True)
    original_hash = module.tree_digest(source)
    with tempfile.TemporaryDirectory(prefix="launcher-text-check-") as directory:
        work = Path(directory)
        ui = prepare_ui(module, source, work, args.unpatched)
        env = {"DMS_LAUNCHER_EVIDENCE": str(work / "evidence.png")} if args.evidence else {}
        logs = run_isolated(work, ui, "launcher-text-bounds.qml", env)
        if args.evidence and (work / "evidence.png").exists():
            shutil.copyfile(work / "evidence.png", args.evidence)
        assert "LAUNCHER_TEXT_PASS" in logs, logs
        assert module.tree_digest(source) == original_hash, "Check changed the input UI"
        print(next(line for line in logs.splitlines() if "LAUNCHER_TEXT_PASS" in line))
        if not args.unpatched:
            print("PASS: renderer tamper/version fallback, repeat staging, unchanged input source")


if __name__ == "__main__":
    main()
