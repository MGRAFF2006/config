#!/usr/bin/env python3
"""Exercise managed auth control flow with real libpam and simulated auth results.

No camera, passwords, root privileges or live PAM changes are needed. pam_exec
records which modules libpam reaches, substituting only the module operation.
The lock stack's pam_unix line also runs for real, against fake accounts in a
bubblewrap user namespace. Also runs the installer's DMS settings step against
fixture homes.
"""

import argparse
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MANAGED_LOCK = "/etc/pam.d/dankshell"


SECOND_FACTOR = {"enableU2f": True, "u2fMode": "and"}
# A stand-in for the running DMS shell: `dms run` starts it as qs with
# DMS_POLICY_LOCK_SETTINGS in its environment. "private" makes it non-dumpable,
# so another process of the same user cannot read its environment.
FAKE_SHELL = """
import ctypes, os, sys, time
libc = ctypes.CDLL(None)
libc.prctl(15, sys.argv[1].encode(), 0, 0, 0)  # PR_SET_NAME
if sys.argv[2] == "private":
    libc.prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE
os.write(1, b"r")
time.sleep(600)
"""
# Runs the real editor in a private PID namespace (so the host's own DMS never
# decides a case), next to the fake shells, with its policy files moved into
# the fixture so the host's /usr/share/dms and /etc/dms never decide one either.
EDITOR = """
import importlib.util, json, subprocess, sys
from pathlib import Path
script, setup, *args = sys.argv[1:]
setup = json.loads(setup)
for name, mode, environment in setup["processes"]:
    shell = subprocess.Popen([sys.executable, "-I", "-c", setup["fake_shell"], name, mode],
                             env=environment, stdout=subprocess.PIPE)
    assert shell.stdout.read(1) == b"r"
spec = importlib.util.spec_from_file_location("configure_dms_lock_pam", script)
editor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(editor)
editor.POLICY_PATHS = tuple(Path(path) for path in setup["policies"])
editor.PAM_DIRS = tuple(Path(path) for path in setup["pam_dirs"])
sys.argv = [script, *args]
sys.exit(editor.main())
"""
PAD = {"padding": "x" * 65536}  # larger than FSIZE_LIMIT
FSIZE_LIMIT = 16384
EDITOR_SCRIPT = ROOT / "scripts/configure-dms-lock-pam.py"
LEGACY_TEXT = json.dumps({"lockPamPath": "/etc/pam.d/legacy-untouched"}) + "\n"


def limit_file_size():
    """A write past the limit fails with EFBIG (Python ignores SIGXFSZ)."""
    resource.setrlimit(resource.RLIMIT_FSIZE, (FSIZE_LIMIT, FSIZE_LIMIT))


def private_pids(command):
    """The command in its own PID namespace with a fresh /proc."""
    bwrap = shutil.which("bwrap")
    assert bwrap, "bwrap is required to keep the host's processes out of the check"
    return [bwrap, "--bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--unshare-pid",
            "--die-with-parent", *command]


def write_fixture(path, contents):
    """dict/list as JSON, str or bytes verbatim, None as a directory."""
    if contents is None:
        path.mkdir()
    elif isinstance(contents, bytes):
        path.write_bytes(contents)
    else:
        path.write_text(contents if isinstance(contents, str) else json.dumps(contents), encoding="utf-8")


def invoke_editor(config, policy_paths=(), processes=(), check=False, env=None, limit=False, pam_dirs=()):
    """The editor on CONFIG_HOME=config in a private PID namespace. policy_paths
    replace its cli-policy.json paths; see run_editor for the rest."""
    environment = {key: value for key, value in os.environ.items() if key != "DMS_POLICY_LOCK_SETTINGS"}
    shells = [(name, mode, {"PATH": environment["PATH"], **({} if value is None else {"DMS_POLICY_LOCK_SETTINGS": value})})
              for name, mode, value in processes]
    setup = json.dumps({"policies": [str(path) for path in policy_paths], "processes": shells,
                        "fake_shell": FAKE_SHELL, "pam_dirs": [str(path) for path in pam_dirs]})
    command = private_pids([sys.executable, "-I", "-c", EDITOR, str(EDITOR_SCRIPT), setup,
                            *(["--check"] if check else []), str(config)])
    if env is not None:
        environment["DMS_POLICY_LOCK_SETTINGS"] = env
    return subprocess.run(command, capture_output=True, text=True, env=environment, timeout=60,
                          preexec_fn=limit_file_size if limit else None)


def run_editor(config, before, legacy="absent", overlays=(), check=False, policy=(None, None), env=None,
               processes=(), limit=False, pam=None):
    """before: settings.json (a dict gets "other": 1 added; None means no file).
    legacy: "absent", "separate" (its own file) or "symlink" (laptop layout).
    overlays: (name, contents) in dms/config.d. policy: (packaged, administrator)
    cli-policy.json contents. env: DMS_POLICY_LOCK_SETTINGS for the editor.
    processes: (name, "readable"|"private", DMS_POLICY_LOCK_SETTINGS or None)
    running next to it as the same user. pam: {name: text} as the editor's
    /etc/pam.d (an empty one by default)."""
    shutil.rmtree(config.parent / "policy", ignore_errors=True)
    shutil.rmtree(config.parent / "pam", ignore_errors=True)
    (config.parent / "pam").mkdir()
    for name, text in (pam or {}).items():
        (config.parent / "pam" / name).write_text(text)
    shutil.rmtree(config, ignore_errors=True)
    canonical = config / "dms/settings.json"
    if before is not None:
        canonical.parent.mkdir(parents=True)
        write_fixture(canonical, {"other": 1, **before} if isinstance(before, dict) else before)
    for name, contents in overlays:
        (config / "dms/config.d").mkdir(parents=True, exist_ok=True)
        write_fixture(config / "dms/config.d" / name, contents)
    if legacy == "separate":
        (config / "DankMaterialShell").mkdir(parents=True)
        (config / "DankMaterialShell/settings.json").write_text(LEGACY_TEXT)
    elif legacy == "symlink":
        (config / "DankMaterialShell").symlink_to("dms")
    policy_paths = [config.parent / "policy" / name for name in ("packaged.json", "admin.json")]
    for path, contents in zip(policy_paths, policy):
        if contents is not None:
            path.parent.mkdir(exist_ok=True)
            write_fixture(path, contents)
    original = canonical.read_bytes() if canonical.is_file() else None
    result = invoke_editor(config, policy_paths, processes, check, env, limit, (config.parent / "pam",))
    if legacy == "separate":
        assert (config / "DankMaterialShell/settings.json").read_text() == LEGACY_TEXT, "edited the legacy file"
    return result, canonical, original


def assert_unchanged(case, result, canonical, original, status, needle):
    assert result.returncode == status, (case, result.returncode, result.stderr)
    assert needle in result.stderr and "Nothing was changed" in result.stderr, (case, result.stderr)
    assert (canonical.read_bytes() if canonical.is_file() else None) == original, ("wrote settings", case)


# Each of these let aff35d0 drop a required security key or misreport a write.
def regression_nan_overlay(config):
    """Qt rejects an overlay with a bare NaN, so DMS keeps settings.json's "and";
    Python's json read the overlay's "or" and migrated."""
    case = run_editor(config, SECOND_FACTOR, overlays=(("90-or.json", '{"u2fMode": "or", "x": NaN}'),))
    assert_unchanged("NaN overlay", *case, 1, "90-or.json")


def regression_policy_key_casing(config):
    """DMS's Go decoder also matches LOCK_SETTINGS (any letter case)."""
    case = run_editor(config, {}, policy=(None, {"LOCK_SETTINGS": SECOND_FACTOR}))
    assert_unchanged("LOCK_SETTINGS", *case, 2, "admin.json: enableU2f = true")


def regression_running_shell(config):
    """A running DMS keeps the lock policy it was launched with."""
    case = run_editor(config, {}, processes=(("qs", "readable", json.dumps(SECOND_FACTOR)),))
    assert_unchanged("running shell", *case, 2, "DMS_POLICY_LOCK_SETTINGS of running qs")


def regression_failure_after_rename(config):
    """The directory flush fails after settings.json was replaced: say it changed."""
    run_editor(config, {})  # creates the fixture
    canonical = config / "dms/settings.json"
    canonical.write_text("{}\n")
    canonical.parent.chmod(0o300)  # rename works; opening the directory to fsync it fails
    try:
        result = invoke_editor(config)
    finally:
        canonical.parent.chmod(0o700)
    assert result.returncode == 1, result
    assert json.loads(canonical.read_text())["lockPamPath"] == MANAGED_LOCK, "the rename did not happen"
    assert "WAS changed" in result.stderr and "unchanged" not in result.stderr, result.stderr


# Each of these let b03ab01 drop a required security key or damage settings.
def regression_pam_security_key(config):
    """An empty lockPamPath makes DMS use login; a key there (or in a stack this
    replaces, or anything they include) would be dropped by the managed stacks."""
    key_stack = "auth required pam_unix.so\nauth required pam_u2f.so cue\n"
    for before, pam, needle in (
        ({"lockPamPath": ""}, {"login": "auth include system-local-login\n", "system-local-login": key_stack},
         "system-local-login:2"),
        ({}, {"dankshell": key_stack}, "dankshell:2"),
        ({"lockPamPath": "/etc/pam.d/custom-lock"}, {"greetd": "-auth [success=1 default=ignore] pam_u2f.so\n"}, "greetd:1"),
    ):
        case = run_editor(config, before, pam=pam)
        assert_unchanged(("PAM key", pam), *case, 2, needle)
    # A smartcard module in a stack nothing here uses does not count.
    result, _, _ = run_editor(config, {}, pam={"kde-smartcard": "auth required pam_pkcs11.so\n"})
    assert result.returncode == 0, result.stderr


def regression_out_of_range_number(config):
    """1e400 parses as inf and was written back as Infinity, which is not JSON."""
    case = run_editor(config, '{"lockPamPath": "", "scale": 1e400}')
    assert_unchanged("1e400", *case, 1, "out of range")


def regression_concurrent_save(config):
    """A DMS save between reading and replacing settings.json must not be undone."""
    spec = importlib.util.spec_from_file_location("configure_dms_lock_pam", EDITOR_SCRIPT)
    editor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(editor)
    run_editor(config, {})  # creates the fixture
    canonical = config / "dms/settings.json"
    original = canonical.read_bytes()
    canonical.write_text('{"theme": "saved by DMS meanwhile"}\n')
    try:
        editor.write_atomically(canonical, {"lockPamPath": MANAGED_LOCK}, original)
    except editor.WriteError as error:
        assert not error.replaced and "changed while this ran" in str(error), error
    else:
        raise AssertionError("replaced settings.json that DMS had saved meanwhile")
    assert json.loads(canonical.read_text()) == {"theme": "saved by DMS meanwhile"}
    assert not [path for path in canonical.parent.iterdir() if path.name.endswith(".tmp")], "left a temporary file"


REGRESSIONS = (regression_nan_overlay, regression_policy_key_casing, regression_running_shell,
               regression_failure_after_rename, regression_pam_security_key,
               regression_out_of_range_number, regression_concurrent_save)


def check_settings_editor():
    """The installer edits the settings file DMS 2.1 reads, never replacing a custom
    stack, and refuses on any DMS security-key setting that is not clearly off."""
    installer = (ROOT / "scripts/install-pam-keyring-howdy.sh").read_text()
    assert 'scripts/configure-dms-lock-pam.py" "$dms_config_home"' in installer, "installer no longer runs the settings step"
    flags = {"greeterPamExternallyManaged": True, "lockPamExternallyManaged": True}
    cases = (
        ({}, MANAGED_LOCK),
        ({"lockPamPath": ""}, MANAGED_LOCK),
        ({**flags, "lockPamPath": MANAGED_LOCK}, MANAGED_LOCK),
        ({"lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
        ({**flags, "lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
        # Security-key settings that are clearly off, and a fingerprint alternative.
        ({"enableU2f": False, "u2fMode": "or", "greeterEnableU2f": False, "lockPamInlineU2f": False,
          "lockU2fPamPath": "", "lockScreenSecurityKeyShortcut": "Ctrl+Q"}, MANAGED_LOCK),
        ({"enableU2f": None, "u2fMode": None}, MANAGED_LOCK),
        ({"enableFprint": True}, MANAGED_LOCK),
    )
    with tempfile.TemporaryDirectory(prefix="howdy-settings-check-") as directory:
        config = Path(directory) / "config"
        for legacy in ("absent", "separate", "symlink"):
            for before, expected in cases:
                result, canonical, original = run_editor(config, before, legacy)
                assert result.returncode == 0, (before, legacy, result.stderr)
                after = json.loads(canonical.read_text())
                assert after["lockPamPath"] == expected, (before, legacy, after)
                assert all(after[key] is True for key in flags), (before, legacy, after)
                assert after["other"] == 1, (before, legacy, after)
                custom = expected != MANAGED_LOCK
                assert custom == ("kept custom lockPamPath" in result.stderr), (before, result.stderr)
                assert ("enableFprint" in before) == ("fingerprint unlock is not offered" in result.stderr), (before, result.stderr)
                if before.keys() >= flags.keys() and before.get("lockPamPath"):
                    assert canonical.read_bytes() == original, ("rewrote unchanged settings", before, legacy)
                result, canonical, original = run_editor(config, before, legacy, check=True)
                assert result.returncode == 0 and canonical.read_bytes() == original, ("--check", before, result)
        # Inputs that do not mention a security key, a running shell without one,
        # and overlays that DMS may apply over settings.json (warned, not refused).
        result, canonical, _ = run_editor(
            config, {}, overlays=((".hidden", {"lockPamPath": "/etc/pam.d/other"}), ("notes.txt", "")),
            policy=({"lock_settings": {"enableU2f": False}}, {"immutable_system": True}), env="{}",
            processes=(("qs", "readable", None), ("quickshell", "readable", '{"u2fMode": "or"}')))
        assert result.returncode == 0, result
        assert "config.d/.hidden sets lockPamPath, which DMS may apply" in result.stderr, result.stderr

        # A security-key setting anywhere, in any letter case and at any depth, that
        # is not clearly off refuses before anything is written, even where DMS
        # would not use it (another overlay turns it off, OR mode, the key off).
        refused = (
            ((SECOND_FACTOR, ()), "enableU2f = true"),
            (({**SECOND_FACTOR, **flags, "lockPamPath": MANAGED_LOCK}, ()), "lockPamExternallyManaged is already true"),
            (({**SECOND_FACTOR, "lockPamPath": "/etc/pam.d/custom-lock"}, ()), 'u2fMode = "and"'),
            (({"enableU2f": True, "u2fMode": "or"}, ()), "enableU2f = true"),
            (({"enableU2f": False, "u2fMode": "and"}, ()), 'u2fMode = "and"'),
            (({"u2fMode": "OR"}, ()), 'u2fMode = "OR"'),
            (({"enableU2f": 0}, ()), "enableU2f = 0"),
            (({"greeterEnableU2f": True}, ()), "greeterEnableU2f = true"),
            (({"lockPamInlineU2f": True}, ()), "lockPamInlineU2f = true"),
            (({"lockU2fPamPath": "/etc/pam.d/key"}, ()), "lockU2fPamPath"),
            (({"ENABLEU2F": True}, ()), "ENABLEU2F = true"),
            (({"plugins": [{"x": {"enableu2f": True}}]}, ()), "enableu2f = true"),
            (({}, (("10-key.json", {"enableU2f": True}), ("20-mode.json", {"u2fMode": "and"}))), "10-key.json"),
            ((SECOND_FACTOR, (("90-or.json", {"u2fMode": "or", "enableU2f": False}),)), "settings.json: enableU2f"),
            # Files DMS would not load still count.
            (({}, ((".90-key.json", SECOND_FACTOR),)), ".90-key.json"),
            (({}, (("90-key.JSON", SECOND_FACTOR),)), "90-key.JSON"),
            (({}, (("key.txt", SECOND_FACTOR),)), "key.txt"),
        )
        for legacy in ("absent", "symlink"):
            for (before, overlays), needle in refused:
                for check in (False, True):
                    case = run_editor(config, before, legacy, overlays, check)
                    assert_unchanged((before, overlays, check), *case, 2, needle)
        # Policy files and DMS_POLICY_LOCK_SETTINGS (the installer's or a running
        # shell's), whatever their key case or nulls, and with no settings.json yet.
        for before, policy, env, processes, needle in (
            ({}, (None, {"lock_settings": SECOND_FACTOR}), None, (), "admin.json"),
            ({}, ({"lock_settings": SECOND_FACTOR}, {"lock_settings": {"u2fMode": None}}), None, (), "packaged.json"),
            ({}, (None, {"Lock_Settings": {"u2fmode": "and"}}), None, (), "admin.json: u2fmode"),
            (None, (None, {"lock_settings": SECOND_FACTOR}), None, (), "admin.json"),
            ({}, (None, None), json.dumps(SECOND_FACTOR), (), "$DMS_POLICY_LOCK_SETTINGS: "),
            ({}, (None, None), None, (("quickshell", "readable", '{"enableU2f": true}'),), "running quickshell"),
            (None, (None, None), None, (("qs", "readable", json.dumps(SECOND_FACTOR)),), "running qs"),
        ):
            for check in (False, True):
                case = run_editor(config, before, policy=policy, env=env, processes=processes, check=check)
                assert_unchanged((before, policy, env, processes), *case, 2, needle)

        # An input that is unreadable or not strict JSON is named and stops the
        # editor without writing, instead of being read differently from DMS.
        for before, overlays, policy, env, processes, needle in (
            ({}, (("50.json", b'{"u2fMode": "or\xff"}'),), (None, None), None, (), "50.json is not valid UTF-8"),
            ({}, (("50.json", '﻿{"u2fMode": "or"}'),), (None, None), None, (), "50.json"),
            ({}, (("50.json", '{"u2fMode": "and", "u2fMode": "or"}'),), (None, None), None, (), "duplicate key 'u2fMode'"),
            ({}, (("50.json", "{not json"),), (None, None), None, (), "50.json"),
            ('{"enableU2f": true, "enableU2f": false}', (), (None, None), None, (), "settings.json"),
            ({}, (), (None, '{"lock_settings": {"x": Infinity}}'), None, (), "admin.json"),
            ({}, (), (None, None), '{"u2fMode": -Infinity}', (), "$DMS_POLICY_LOCK_SETTINGS"),
            ({}, (), (None, None), None, (("qs", "readable", "{"),), "running qs"),
            ({}, (), (None, None), None, (("qs", "private", "{}"),), "cannot inspect running process"),
        ):
            case = run_editor(config, before, overlays=overlays, policy=policy, env=env, processes=processes)
            assert_unchanged(needle, *case, 1, needle)
        (config / "dms/config.d").mkdir()
        (config / "dms/config.d/gone.json").symlink_to("missing.json")
        result = invoke_editor(config)
        assert result.returncode == 1 and "gone.json is not a regular file" in result.stderr, result
        for regression in REGRESSIONS:
            regression(config)

        # The write replaces the file atomically: a failed write (here, a file size
        # limit) leaves the original intact and fails; mode and a symlink are kept.
        result, canonical, original = run_editor(config, PAD, limit=True)
        assert result.returncode == 1 and "The file is unchanged" in result.stderr, ("failed write not reported", result)
        assert canonical.read_bytes() == original, "a failed write changed the settings file"
        assert sorted(path.name for path in canonical.parent.iterdir()) == ["settings.json"], "left a temporary file"
        result, canonical, original = run_editor(config, {})
        canonical.chmod(0o640)
        moved = config / "dotfiles/dms-settings.json"
        moved.parent.mkdir()
        canonical.rename(moved)
        canonical.symlink_to(moved)
        moved.write_bytes(original)
        result = invoke_editor(config)
        assert result.returncode == 0, result
        assert canonical.is_symlink() and json.loads(moved.read_text())["lockPamPath"] == MANAGED_LOCK
        assert moved.stat().st_mode & 0o7777 == 0o640, oct(moved.stat().st_mode)

        # DMS has not created its settings yet: warn and fail without writing anywhere.
        for legacy in ("absent", "separate"):
            result, canonical, _ = run_editor(config, None, legacy)
            assert result.returncode == 3 and "not found" in result.stderr, (legacy, result)
            assert not canonical.exists(), legacy
    print("PASS: installer settings: DMS 2.1 settings file selected (legacy path ignored), custom lockPamPath preserved; "
          "any security-key setting not clearly off (any case or depth, in settings.json, every config.d file, a "
          "policy file, DMS_POLICY_LOCK_SETTINGS here or in a running shell) refused without changes; non-strict "
          "or unreadable inputs refused by name; atomic write keeps the file on failure and reports a failure "
          "after the rename as a change")


# The laptop's PAM on 2026-11-24 after the approved interim fix: greetd and
# dankshell password-only (pam_howdy removed), stock pambase system-auth. Its
# sudo is the managed Howdy-first file, added from the repository below.
LIVE_INTERIM = {
    "greetd": "auth required pam_securetty.so\nauth requisite pam_nologin.so\n"
              "auth [success=1 default=ignore] pam_unix.so try_first_pass nullok\nauth requisite pam_deny.so\n",
    "dankshell": "auth requisite pam_nologin.so\nauth required pam_shells.so\n"
                 "auth [success=1 default=ignore] pam_unix.so try_first_pass nullok\nauth requisite pam_deny.so\n",
    "system-auth": "auth required pam_faillock.so preauth\n-auth [success=2 default=ignore] pam_systemd_home.so\n"
                   "auth [success=1 default=bad] pam_unix.so try_first_pass nullok\n"
                   "auth [default=die] pam_faillock.so authfail\nauth optional pam_permit.so\n",
}
INSTALLED = ("greetd", "sddm", "dankshell", "sudo", "polkit-1")


def check_installer(pam_root):
    """Run the real installer as namespace root against throwaway /etc/pam.d,
    /etc/howdy and DMS settings: it refuses a DMS second factor before writing
    anything, and it applies cleanly from the laptop's interim password-only state."""
    bwrap = shutil.which("bwrap")
    assert bwrap, "bwrap is required to run the installer against throwaway system directories"
    with tempfile.TemporaryDirectory(prefix="howdy-installer-check-") as directory:
        root = Path(directory)
        fakes = root / "fakes"
        (fakes / "security").mkdir(parents=True)
        for module in ("pam_howdy.so", "pam_kwallet5.so"):  # presence checks only
            (fakes / "security" / module).write_text("")
        (fakes / "python").mkdir()
        (fakes / "python/dlib.py").write_text("")

        def run(settings, limit=False, config_arg=True):
            for name in ("pam.d", "howdy", "config"):
                shutil.rmtree(root / name, ignore_errors=True)
                (root / name).mkdir()
            for name, text in LIVE_INTERIM.items():
                (root / "pam.d" / name).write_text(text)
            shutil.copyfile(pam_root / "sudo", root / "pam.d/sudo")
            (root / "config/dms").mkdir()
            (root / "config/dms/settings.json").write_text(json.dumps(settings) + "\n")
            before = {path.name: path.read_bytes() for path in (root / "pam.d").iterdir()}
            command = [bwrap, "--unshare-user", "--uid", "0", "--gid", "0", "--unshare-pid", "--ro-bind", "/", "/",
                       "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--die-with-parent",
                       "--bind", str(root / "pam.d"), "/etc/pam.d", "--bind", str(root / "howdy"), "/etc/howdy",
                       "--ro-bind", str(fakes / "security"), "/usr/lib/security", "--tmpfs", "/usr/lib/howdy",
                       "--bind", str(root / "config"), str(root / "config"),
                       "--setenv", "PYTHONPATH", str(fakes / "python"),
                       "--unsetenv", "SUDO_USER",
                       "bash", str(ROOT / "scripts/install-pam-keyring-howdy.sh"),
                       *([str(root / "config")] if config_arg else [])]
            result = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                    preexec_fn=limit_file_size if limit else None)
            return result, before

        settings = {"lockPamPath": MANAGED_LOCK, "lockPamExternallyManaged": True, "greeterPamExternallyManaged": True}
        result, before = run({**settings, **SECOND_FACTOR})
        assert result.returncode != 0, ("installer went ahead with a DMS second factor", result.stdout, result.stderr)
        assert "security key" in result.stderr, result.stderr
        after = {path.name: path.read_bytes() for path in (root / "pam.d").iterdir()}
        assert after == before, ("PAM changed although the installer refused", sorted(after))
        assert not any((root / "howdy").iterdir()), "Howdy config written although the installer refused"
        assert json.loads((root / "config/dms/settings.json").read_text()) == {**settings, **SECOND_FACTOR}

        # Root without a DMS user (e.g. a root login shell): nothing to check the
        # security-key settings against, so refuse before replacing greetd/dankshell.
        result, before = run({}, config_arg=False)
        assert result.returncode != 0 and "No DMS user" in result.stderr, (result.stdout, result.stderr)
        after = {path.name: path.read_bytes() for path in (root / "pam.d").iterdir()}
        assert after == before, ("PAM changed without a DMS user to check", sorted(after))

        # The settings write fails (file size limit): the installer stops with an
        # error before any PAM or Howdy change, and the settings file is intact.
        result, before = run(PAD, limit=True)
        assert result.returncode != 0, ("installer reported success after a failed settings write", result.stdout, result.stderr)
        assert "DMS settings step failed" in result.stderr and "Done" not in result.stdout, result
        after = {path.name: path.read_bytes() for path in (root / "pam.d").iterdir()}
        assert after == before, ("PAM changed although the settings write failed", sorted(after))
        assert not any((root / "howdy").iterdir()), "Howdy config written although the settings write failed"
        assert json.loads((root / "config/dms/settings.json").read_text()) == PAD, "failed write damaged settings.json"

        # From the live interim state (password-only greetd/dankshell, stock
        # system-auth, Howdy-first sudo) the installer restores the managed files.
        for initial in (settings, {}):
            result, before = run(initial)
            assert result.returncode == 0, (initial, result.stdout, result.stderr)
            for name in INSTALLED:
                assert (root / "pam.d" / name).read_bytes() == (pam_root / name).read_bytes(), (initial, name)
            for name, text in before.items():
                if name != "system-auth":
                    assert [p.read_bytes() for p in (root / "pam.d").glob(f"{name}.backup-*")] == [text], (initial, name)
            assert (root / "pam.d/system-auth").read_bytes() == before["system-auth"], "system-auth changed"
            assert (root / "pam.d/sudo").read_bytes() == before["sudo"], "sudo changed"
            assert "system-auth still has an active pam_howdy" not in result.stdout + result.stderr
            assert (root / "howdy/config.ini").read_bytes() == (ROOT / "system/howdy/config.ini").read_bytes()
            assert json.loads((root / "config/dms/settings.json").read_text()) == settings, initial
    check_installer_caller_environment()
    print("PASS: installer: refuses a DMS second factor before writing any file (including one only in the "
          "caller's DMS_POLICY_LOCK_SETTINGS, before sudo); stops before PAM when the settings write fails; "
          "applies from the interim password-only state (system-auth untouched, backups kept, sudo reinstalled unchanged)")


def check_installer_caller_environment():
    """sudo drops DMS_POLICY_LOCK_SETTINGS, so the unprivileged installer checks
    with the caller's environment before it re-runs itself through sudo."""
    assert os.geteuid() != 0, "run as an unprivileged user: this case needs the sudo re-exec path"
    with tempfile.TemporaryDirectory(prefix="howdy-installer-env-check-") as directory:
        root = Path(directory)
        (root / "bin").mkdir()
        (root / "bin/sudo").write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > {root / "sudo-called"}\n')
        (root / "bin/sudo").chmod(0o755)
        (root / "config/dms").mkdir(parents=True)
        (root / "config/dms/settings.json").write_text("{}\n")
        for env, escalates in ((json.dumps(SECOND_FACTOR), False), (None, True)):
            (root / "sudo-called").unlink(missing_ok=True)
            environment = {key: value for key, value in os.environ.items() if key != "DMS_POLICY_LOCK_SETTINGS"}
            environment.update(PATH=f"{root / 'bin'}:{environment['PATH']}", XDG_CONFIG_HOME=str(root / "config"))
            if env is not None:
                environment["DMS_POLICY_LOCK_SETTINGS"] = env
            result = subprocess.run(private_pids(["bash", str(ROOT / "scripts/install-pam-keyring-howdy.sh")]),
                                    capture_output=True, text=True, env=environment, timeout=60)
            assert (root / "sudo-called").exists() == escalates, (env, result.stdout, result.stderr)
            if escalates:
                assert result.returncode == 0, result
                assert (root / "sudo-called").read_text().split("\n")[-2] == str(root / "config"), "config home not passed"
            else:
                assert result.returncode != 0 and "DMS_POLICY_LOCK_SETTINGS" in result.stderr, result


pam = ctypes.CDLL("libpam.so.0")
conversation = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


class Conversation(ctypes.Structure):
    _fields_ = [("callback", conversation), ("data", ctypes.c_void_p)]


pam.pam_start_confdir.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(Conversation), ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
pam.pam_authenticate.argtypes = [ctypes.c_void_p, ctypes.c_int]
pam.pam_end.argtypes = [ctypes.c_void_p, ctypes.c_int]

BLANK_USER, SECRET_USER = "howdy-check-blank", "howdy-check-secret"
SECRET = "correct-test-password"
# openssl passwd -6 -salt howdycheck correct-test-password
SECRET_HASH = "$6$howdycheck$f00Do71TijHH6sFWun1Nc6gwmEz5vSFKxvQCZfbxNkVfUiPKRO/IBYYB6LdYDr68PM7cmYScP6ganTL8MYY3d."
STUB = '#!/bin/sh\nprintf "%s\\n" "$2" >> "$1"\n[ "$3" = stall ] && { sleep 20; exit 1; }\nexit "$3"\n'


class Message(ctypes.Structure):
    _fields_ = [("style", ctypes.c_int), ("text", ctypes.c_char_p)]


class Response(ctypes.Structure):
    _fields_ = [("resp", ctypes.c_void_p), ("retcode", ctypes.c_int)]


def real_unix_child(directory):
    """Runs inside the user namespace: real pam_unix, stubbed Howdy and guards."""
    libc = ctypes.CDLL(None)
    libc.calloc.restype = ctypes.c_void_p
    libc.calloc.argtypes = [ctypes.c_size_t, ctypes.c_size_t]
    libc.strdup.restype = ctypes.c_void_p
    libc.strdup.argtypes = [ctypes.c_char_p]
    root = Path(directory)
    trace = root / "trace"
    lines, cases = json.loads((root / "cases.json").read_text())
    results = []
    for user, answer, face, nullok in cases:
        prompts = []

        @conversation
        def reply(count, messages, responses, data):
            replies = ctypes.cast(libc.calloc(count, ctypes.sizeof(Response)), ctypes.POINTER(Response))
            for i in range(count):
                message = ctypes.cast(messages, ctypes.POINTER(ctypes.POINTER(Message)))[i].contents
                if message.style in (1, 2):  # PAM_PROMPT_ECHO_OFF / ECHO_ON
                    prompts.append(message.style)
                    replies[i].resp = libc.strdup(answer.encode())
            ctypes.cast(responses, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.cast(replies, ctypes.c_void_p)
            return 0

        stack = []
        for kind, control, name, options in lines:
            if name == "pam_unix.so":
                stack.append(f"{kind} {control} {name} {options}{' nullok' if nullok else ''}")
            elif name == "pam_deny.so":
                stack.append(f"{kind} {control} {name}")
            else:
                code = 1 if name == "pam_howdy.so" and not face else 0
                stack.append(f"{kind} {control} pam_exec.so quiet /bin/sh {root / 'module.sh'} {trace} {name} {code}")
        (root / "check").write_text("\n".join(stack) + "\n")
        trace.write_text("")
        conv = Conversation(reply, None)
        handle = ctypes.c_void_p()
        result = pam.pam_start_confdir(b"check", user.encode(), ctypes.byref(conv), str(root).encode(), ctypes.byref(handle))
        assert result == 0, ("pam_start_confdir", result)
        try:
            result = pam.pam_authenticate(handle, 0)  # Quickshell passes no flags either.
        finally:
            pam.pam_end(handle, result)
        results.append({"success": result == 0, "prompts": len(prompts), "howdy": "pam_howdy.so" in trace.read_text().split()})
    print(json.dumps(results))


def check_real_unix(pam_root):
    """The automatic lock attempt answers with an empty password; only Howdy may accept it."""
    bwrap = shutil.which("bwrap")
    assert bwrap, "bwrap is required to run real pam_unix against fake accounts"
    lines = [list(re.match(r"(-?auth)\s+(\[[^]]+\]|\S+)\s+(\S+)\s*(.*)", line).groups())
             for line in (pam_root / "dankshell").read_text().splitlines() if re.match(r"-?auth\s", line)]
    # (user, answer, face matches, add nullok as a negative control) -> (unlocks, Howdy reached)
    cases = (
        ((BLANK_USER, "", False, False), (False, True)),
        ((BLANK_USER, "", True, False), (True, True)),
        ((SECRET_USER, "", False, False), (False, True)),
        ((SECRET_USER, "", True, False), (True, True)),
        ((SECRET_USER, SECRET, False, False), (True, False)),
        # Control: proves the fake blank account is read; nullok skips Howdy.
        ((BLANK_USER, "", False, True), (True, False)),
    )
    with tempfile.TemporaryDirectory(prefix="howdy-unix-check-") as directory:
        root = Path(directory)
        (root / "module.sh").write_text(STUB)
        (root / "module.sh").chmod(0o755)
        (root / "passwd").write_text(f"root:x:0:0::/root:/bin/sh\n{BLANK_USER}:x:4242:4242::/nonexistent:/bin/sh\n{SECRET_USER}:x:4243:4243::/nonexistent:/bin/sh\n")
        (root / "shadow").write_text(f"root:!*:1::::::\n{BLANK_USER}::1::::::\n{SECRET_USER}:{SECRET_HASH}:1::::::\n")
        (root / "group").write_text("root:x:0:\nhowdy-check:x:4242:\n")
        (root / "nsswitch.conf").write_text("passwd: files\ngroup: files\nshadow: files\n")
        (root / "cases.json").write_text(json.dumps([lines, [case for case, _ in cases]]))
        command = [bwrap, "--unshare-user", "--uid", "0", "--gid", "0", "--ro-bind", "/", "/", "--dev", "/dev",
                   "--proc", "/proc", "--tmpfs", "/tmp", "--bind", str(root), str(root), "--die-with-parent"]
        for name in ("passwd", "shadow", "group", "nsswitch.conf"):
            command += ["--ro-bind", str(root / name), f"/etc/{name}"]
        command += [sys.executable, "-I", str(Path(__file__).resolve()), "--real-unix-child", str(root)]
        output = subprocess.run(command, capture_output=True, text=True, check=True, timeout=60).stdout
        for (case, (unlocks, howdy)), result in zip(cases, json.loads(output), strict=True):
            assert result["success"] == unlocks, ("dankshell real pam_unix", case, result)
            assert result["howdy"] == howdy, ("dankshell real pam_unix", case, result)
            if not case[3]:
                assert result["prompts"] == 1, ("pam_unix must ask before Howdy", case, result)
    print("PASS: dankshell: real pam_unix rejects an empty answer, even for a blank-password account; only Howdy accepts it")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pam-root", type=Path, default=Path(__file__).resolve().parents[1] / "system/pam.d")
    parser.add_argument("--real-unix-child", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.real_unix_child:
        real_unix_child(args.real_unix_child)
        return

    @conversation
    def unexpected_prompt(count, messages, responses, data):
        return 19  # PAM_CONV_ERR: simulated modules should never prompt.

    conv = Conversation(unexpected_prompt, None)
    with tempfile.TemporaryDirectory(prefix="howdy-pam-check-") as directory:
        root = Path(directory)
        trace = root / "trace"
        module = root / "module.sh"
        # "stall" stands in for a camera that never returns.
        module.write_text(STUB)
        module.chmod(0o755)
        # greetd as the held TPM opt-in installs it: the token supplier after pam_deny.
        spec = importlib.util.spec_from_file_location("enrollment", ROOT / "scripts/install-howdy-kwallet-tpm.py")
        enrollment = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(enrollment)
        stacks = {service: (args.pam_root / service).read_text() for service in ("greetd", "dankshell")}
        stacks["greetd with TPM token"] = enrollment.token_stack(
            stacks["greetd"].encode(), "howdy-test", Path("/nonexistent.cred"), "howdy-test").decode()
        for service, text in stacks.items():
            lines = []
            for line in text.splitlines():
                match = re.match(r"(-?auth)\s+(\[[^]]+\]|\S+)\s+(\S+)", line)
                if match:
                    lines.append(match.groups())

            def authenticate(face, password, failed_guard=None):
                trace.write_text("")
                stack = []
                for kind, control, name in lines:
                    if name == "pam_deny.so":
                        stack.append(f"{kind} {control} {name}")
                        continue
                    result = face if name == "pam_howdy.so" else password if name == "pam_unix.so" else name != failed_guard
                    code = "stall" if result == "stall" else 0 if result else 1
                    stack.append(f"{kind} {control} pam_exec.so quiet /bin/sh {module} {trace} {name} {code}")
                (root / "check").write_text("\n".join(stack) + "\n")
                handle = ctypes.c_void_p()
                result = pam.pam_start_confdir(b"check", b"howdy-test", ctypes.byref(conv), str(root).encode(), ctypes.byref(handle))
                assert result == 0, ("pam_start_confdir", result)
                try:
                    result = pam.pam_authenticate(handle, 0)
                finally:
                    pam.pam_end(handle, result)
                return result == 0, trace.read_text().splitlines()

            # Password first: a correct password never reaches Howdy, so a stalled
            # camera cannot delay it; an empty or wrong one falls through to Howdy.
            for face, password, expected in ((True, False, True), (False, True, True), ("stall", True, True), (False, False, False)):
                started = time.monotonic()
                success, reached = authenticate(face, password)
                assert success == expected, (service, face, password, success, reached)
                methods = [name for name in reached if name in ("pam_howdy.so", "pam_unix.so")]
                assert methods == (["pam_unix.so"] if password else ["pam_unix.so", "pam_howdy.so"]), (service, "order", methods)
                assert time.monotonic() - started < 10, (service, "password waited for a stalled camera")
                if expected:
                    continuation = ["pam_kwallet5.so"] if service == "greetd" else ["pam_env.so"]
                    if service == "greetd with TPM token":
                        continuation = ["pam_howdy_tpm.so", "pam_kwallet5.so"]
                    assert reached[-len(continuation):] == continuation, (service, "skipped continuation", reached)
            # A successful password or face cannot bypass existing prerequisite
            # failures. At greetd the wallet token supplier and KWallet must not
            # even run then: they would unseal and take the wallet password.
            greetd = service.startswith("greetd")
            guards = ("pam_securetty.so", "pam_nologin.so") if greetd else ("pam_nologin.so", "pam_shells.so")
            for guard in guards:
                for face, password in ((True, False), (False, True)):
                    success, reached = authenticate(face, password, guard)
                    assert not success, (service, "bypassed guard", guard, reached)
                    if greetd:
                        assert not {"pam_howdy_tpm.so", "pam_kwallet5.so"} & set(reached), (service, guard, reached)
            print(f"PASS: {service}: password first (independent of a stalled camera), Howdy fallback, deny both failures, continuation and prerequisite guards")
    check_real_unix(args.pam_root)
    check_settings_editor()
    check_installer(args.pam_root)


if __name__ == "__main__":
    main()
