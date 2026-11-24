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
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
MANAGED_LOCK = "/etc/pam.d/dankshell"


SECOND_FACTOR = {"enableU2f": True, "u2fMode": "and"}


def check_settings_editor():
    """The installer edits the settings file DMS 2.1 reads, never replacing a custom
    stack and never dropping a security key that DMS requires as a second factor."""
    installer = (ROOT / "scripts/install-pam-keyring-howdy.sh").read_text()
    assert 'scripts/configure-dms-lock-pam.py" "$dms_config_home"' in installer, "installer no longer runs the settings step"
    script = ROOT / "scripts/configure-dms-lock-pam.py"
    flags = {"greeterPamExternallyManaged": True, "lockPamExternallyManaged": True}
    legacy_text = json.dumps({"lockPamPath": "/etc/pam.d/legacy-untouched"}) + "\n"

    def run(config, before, legacy="absent", overlays=(), check=False):
        """legacy: "absent", "separate" (its own file) or "symlink" (laptop layout).
        overlays: (name, values) written to dms/config.d, which DMS merges on top."""
        shutil.rmtree(config, ignore_errors=True)
        canonical = config / "dms/settings.json"
        if before is not None:
            canonical.parent.mkdir(parents=True)
            canonical.write_text(json.dumps({"other": 1, **before}, indent=2) + "\n")
        for name, values in overlays:
            (config / "dms/config.d").mkdir(parents=True, exist_ok=True)
            (config / "dms/config.d" / name).write_text(json.dumps(values))
        if legacy == "separate":
            (config / "DankMaterialShell").mkdir(parents=True)
            (config / "DankMaterialShell/settings.json").write_text(legacy_text)
        elif legacy == "symlink":
            (config / "DankMaterialShell").symlink_to("dms")
        original = canonical.read_text() if before is not None else None
        command = ["python3", "-I", str(script), *(["--check"] if check else []), str(config)]
        result = subprocess.run(command, capture_output=True, text=True)
        if legacy == "separate":
            assert (config / "DankMaterialShell/settings.json").read_text() == legacy_text, "edited the legacy file"
        return result, canonical, original

    cases = (
        ({}, MANAGED_LOCK),
        ({"lockPamPath": ""}, MANAGED_LOCK),
        ({**flags, "lockPamPath": MANAGED_LOCK}, MANAGED_LOCK),
        ({"lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
        ({**flags, "lockPamPath": "/etc/pam.d/custom-lock"}, "/etc/pam.d/custom-lock"),
        # A key as an alternative, or a second-factor mode with the key off, is no
        # second factor: the migration goes ahead and says what DMS stops offering.
        ({"enableU2f": True, "u2fMode": "or"}, MANAGED_LOCK),
        ({"enableU2f": True}, MANAGED_LOCK),
        ({"enableU2f": False, "u2fMode": "and"}, MANAGED_LOCK),
    )
    with tempfile.TemporaryDirectory(prefix="howdy-settings-check-") as directory:
        config = Path(directory) / "config"
        for legacy in ("absent", "separate", "symlink"):
            for before, expected in cases:
                result, canonical, original = run(config, before, legacy)
                assert result.returncode == 0, (before, legacy, result.stderr)
                after = json.loads(canonical.read_text())
                assert after["lockPamPath"] == expected, (before, legacy, after)
                assert all(after[key] is True for key in flags), (before, legacy, after)
                assert after["other"] == 1, (before, legacy, after)
                custom = expected != MANAGED_LOCK
                assert custom == ("kept custom lockPamPath" in result.stderr), (before, result.stderr)
                assert (before.get("enableU2f") is True) == ("security key (OR) unlock is not offered" in result.stderr), (before, result.stderr)
                if before.keys() >= flags.keys() and before.get("lockPamPath"):
                    assert canonical.read_text() == original, ("rewrote unchanged settings", before, legacy)
                result, canonical, original = run(config, before, legacy, check=True)
                assert result.returncode == 0 and canonical.read_text() == original, ("--check", before, result)

        # DMS requires the key after the password. An externally managed lock makes
        # DMS skip that step and dankshell has no pam_u2f, so refuse and change nothing,
        # whether the policy comes from settings.json or a config.d overlay.
        refused = (
            (SECOND_FACTOR, ()),
            ({**SECOND_FACTOR, **flags, "lockPamPath": MANAGED_LOCK}, ()),
            ({**SECOND_FACTOR, "lockPamPath": "/etc/pam.d/custom-lock"}, ()),
            ({"enableU2f": True}, (("50-key.json", {"u2fMode": "and"}),)),
            ({}, (("10-key.json", {"enableU2f": True}), ("20-mode.json", {"u2fMode": "and"}))),
        )
        for legacy in ("absent", "symlink"):
            for before, overlays in refused:
                for check in (False, True):
                    result, canonical, original = run(config, before, legacy, overlays, check)
                    assert result.returncode == 2, ("dropped the security key", before, overlays, check, result)
                    assert "security key" in result.stderr and "Nothing was changed" in result.stderr, result.stderr
                    assert canonical.read_text() == original, ("wrote settings although refused", before, overlays)
        # A later overlay that turns the second factor off wins, as in DMS.
        result, canonical, _ = run(config, SECOND_FACTOR, overlays=(("90-or.json", {"u2fMode": "or"}),))
        assert result.returncode == 0 and json.loads(canonical.read_text())["lockPamPath"] == MANAGED_LOCK, result

        # DMS has not created its settings yet: warn and fail without writing anywhere.
        for legacy in ("absent", "separate"):
            result, canonical, _ = run(config, None, legacy)
            assert result.returncode == 3 and "not found" in result.stderr, (legacy, result)
            assert not canonical.exists(), legacy
    print("PASS: installer settings: DMS 2.1 settings file selected (legacy path ignored), custom lockPamPath preserved, "
          "a DMS second-factor security key (settings.json or config.d) refused without changes")


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

        def run(settings):
            for name in ("pam.d", "howdy", "config"):
                shutil.rmtree(root / name, ignore_errors=True)
                (root / name).mkdir()
            for name, text in LIVE_INTERIM.items():
                (root / "pam.d" / name).write_text(text)
            shutil.copyfile(pam_root / "sudo", root / "pam.d/sudo")
            (root / "config/dms").mkdir()
            (root / "config/dms/settings.json").write_text(json.dumps(settings) + "\n")
            before = {path.name: path.read_bytes() for path in (root / "pam.d").iterdir()}
            command = [bwrap, "--unshare-user", "--uid", "0", "--gid", "0", "--ro-bind", "/", "/",
                       "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--die-with-parent",
                       "--bind", str(root / "pam.d"), "/etc/pam.d", "--bind", str(root / "howdy"), "/etc/howdy",
                       "--ro-bind", str(fakes / "security"), "/usr/lib/security", "--tmpfs", "/usr/lib/howdy",
                       "--bind", str(root / "config"), str(root / "config"),
                       "--setenv", "PYTHONPATH", str(fakes / "python"),
                       "bash", str(ROOT / "scripts/install-pam-keyring-howdy.sh"), str(root / "config")]
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            return result, before

        settings = {"lockPamPath": MANAGED_LOCK, "lockPamExternallyManaged": True, "greeterPamExternallyManaged": True}
        result, before = run({**settings, **SECOND_FACTOR})
        assert result.returncode != 0, ("installer went ahead with a DMS second factor", result.stdout, result.stderr)
        assert "security key" in result.stderr, result.stderr
        after = {path.name: path.read_bytes() for path in (root / "pam.d").iterdir()}
        assert after == before, ("PAM changed although the installer refused", sorted(after))
        assert not any((root / "howdy").iterdir()), "Howdy config written although the installer refused"
        assert json.loads((root / "config/dms/settings.json").read_text()) == {**settings, **SECOND_FACTOR}

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
    print("PASS: installer: refuses a DMS second factor before writing any file; applies from the interim "
          "password-only state (system-auth untouched, backups kept, sudo reinstalled unchanged)")


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
        for service in ("greetd", "dankshell"):
            lines = []
            for line in (args.pam_root / service).read_text().splitlines():
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
                    continuation = "pam_kwallet5.so" if service == "greetd" else "pam_env.so"
                    assert continuation in reached, (service, "skipped continuation", reached)
            # A successful face cannot bypass existing prerequisite failures.
            guards = ("pam_securetty.so", "pam_nologin.so") if service == "greetd" else ("pam_nologin.so", "pam_shells.so")
            for guard in guards:
                success, reached = authenticate(True, False, guard)
                assert not success, (service, "bypassed guard", guard, reached)
            print(f"PASS: {service}: password first (independent of a stalled camera), Howdy fallback, deny both failures, continuation and prerequisite guards")
    check_real_unix(args.pam_root)
    check_settings_editor()
    check_installer(args.pam_root)


if __name__ == "__main__":
    main()
