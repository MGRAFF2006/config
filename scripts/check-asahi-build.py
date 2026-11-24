#!/usr/bin/env python3
"""Exercise the Asahi build wrapper with a stub make; no Rust or kernel sources needed."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts/asahi-build.sh"
SETUP = ROOT / "scripts/setup-asahi-build.sh"

GOOD_CONFIG = "CONFIG_RUST=y\nCONFIG_ARM64_16K_PAGES=y\nCONFIG_DRM_ASAHI=m\n"
NO_RUST_CONFIG = "# CONFIG_RUST is not set\nCONFIG_ARM64_16K_PAGES=y\n# CONFIG_DRM_ASAHI is not set\n"

# Models the Kbuild parts the wrapper relies on: KCONFIG_CONFIG (relative to
# O=) selects the config, and syncconfig, also run implicitly before any build,
# regenerates include/config/auto.conf. A "drop-rust" file next to the stub
# simulates a toolchain change that makes Kconfig disable Rust and the GPU driver.
STUB_MAKE = r"""#!/bin/bash
here=$(dirname "$0")
args=("$@")
out=
targets=()
while (($#)); do
  case $1 in
    -C) shift ;;
    O=*) out=${1#O=} ;;
    -j*|*=*) ;;
    *) targets+=("$1") ;;
  esac
  shift
done
config=${KCONFIG_CONFIG:-.config}
[[ $config == /* ]] || config=$out/$config
printf 'make%s KCONFIG_CONFIG=%s MAKEFLAGS=%s\n' "$(printf ' %q' "${args[@]}")" \
  "${KCONFIG_CONFIG-unset}" "${MAKEFLAGS-unset}" >> "$here/make.log"
resync() {
  [[ -e $here/drop-rust ]] && printf '%s' "$(cat "$here/no-rust.config")" > "$config"
  mkdir -p "$out/include/config"
  grep -E '^CONFIG_[A-Z0-9_]+=' "$config" > "$out/include/config/auto.conf" || true
}
case ${targets[0]} in
  rustavailable) ;;
  defconfig) cp "$here/good.config" "$config" ;;
  syncconfig) resync ;;
  *)
    resync
    if grep -qx CONFIG_RUST=y "$out/include/config/auto.conf"; then rust=y; else rust=n; fi
    echo "BUILT ${targets[*]} rust=$rust" >> "$here/make.log"
    ;;
esac
"""

STUB_DF = """#!/bin/sh
echo 'Filesystem 1024-blocks Used Available Capacity Mounted on'
echo 'stub 104857600 0 104857600 0% /'
"""


class Fixture:
    def __init__(self, base):
        self.base = Path(base)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        for name, text in (("make", STUB_MAKE), ("df", STUB_DF)):
            (self.bin / name).write_text(text)
            (self.bin / name).chmod(0o755)
        (self.bin / "good.config").write_text(GOOD_CONFIG)
        (self.bin / "no-rust.config").write_text(NO_RUST_CONFIG)
        self.source = self.base / "linux"
        (self.source / "arch/arm64/configs").mkdir(parents=True)
        (self.source / "arch/arm64/configs/asahi.config").write_text("CONFIG_RUST=y\n")
        self.rust_source = self.base / "rust/library"
        (self.rust_source / "core/src").mkdir(parents=True)
        (self.rust_source / "core/src/lib.rs").touch()
        self.home = self.base / "home"
        self.home.mkdir()
        self.output = self.base / "out"

    def log(self):
        path = self.bin / "make.log"
        return path.read_text() if path.exists() else ""

    def clear_log(self):
        (self.bin / "make.log").unlink(missing_ok=True)

    def run(self, *args, env=None, output=None):
        stub = (
            "detect_toolchain() { llvm=1; rustc=/usr/bin/rustc; bindgen=/usr/bin/bindgen; "
            f"rust_source={shlex.quote(str(self.rust_source))}; }}"
        )
        # $0 must differ from the sourced path so the script's own main is not run.
        script = f'source "$1"; shift; {stub}; main "$@"'
        environment = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.home),
            "LANG": "C.UTF-8",
            "ASAHI_OUTPUT": str(output or self.output),
        }
        environment.update(env or {})
        return subprocess.run(
            ["bash", "-c", script, "asahi-build-check", str(WRAPPER), *args],
            env=environment, text=True, capture_output=True,
        )


def expect(result, code, label):
    assert result.returncode == code, (
        f"{label}: exit {result.returncode}, expected {code}\n{result.stdout}{result.stderr}"
    )


def check_wrapper():
    with tempfile.TemporaryDirectory() as base:
        f = Fixture(base)
        source = str(f.source)

        expect(f.run("build", source), 1, "build before configure")
        expect(f.run("configure", source), 0, "configure")
        assert (f.output / ".config").read_text() == GOOD_CONFIG

        # Default and documented targets reach make unchanged.
        f.clear_log()
        expect(f.run("build", source), 0, "default build")
        assert "BUILT Image modules dtbs rust=y" in f.log(), f.log()
        accepted = ["Image", "Image.gz", "modules", "dtbs", "fs/exec.o",
                    "drivers/gpu/drm/asahi/asahi.o", "net/core/skbuff.ko",
                    "kernel/fork.s", "kernel/fork.i", "fs/exec.lst"]
        f.clear_log()
        expect(f.run("build", source, *accepted), 0, "accepted targets")
        assert f"BUILT {' '.join(accepted)} rust=y" in f.log(), f.log()

        # Caller variables must not select another config or change Make.
        bad = f.base / "bad.config"
        bad.write_text(NO_RUST_CONFIG)
        f.clear_log()
        result = f.run("build", source, env={
            "KCONFIG_CONFIG": str(bad), "MAKEFLAGS": "-k", "ARCH": "x86",
        })
        assert "rust=n" not in f.log(), f"alternate KCONFIG_CONFIG built without Rust:\n{f.log()}"
        assert "KCONFIG_CONFIG=unset MAKEFLAGS=unset" in f.log(), f.log()
        assert "KCONFIG_CONFIG=" + str(bad) not in f.log(), f.log()
        expect(result, 0, "build with hostile environment")

        # A resync that drops Rust must stop before compiling anything.
        (f.bin / "drop-rust").touch()
        f.clear_log()
        result = f.run("build", source)
        assert "BUILT" not in f.log(), f"build continued after Rust was dropped:\n{f.log()}"
        expect(result, 1, "resync dropping Rust")
        (f.bin / "drop-rust").unlink()

        # An invalid .config is refused.
        (f.output / ".config").write_text(NO_RUST_CONFIG)
        f.clear_log()
        result = f.run("build", source)
        assert "BUILT" not in f.log(), f.log()
        expect(result, 1, "invalid .config")
        (f.output / ".config").write_text(GOOD_CONFIG)

        # Anything but the allowlisted build targets is refused before Make runs.
        for target in ("rustfmt", "rustfmtcheck", "mrproper", "clean", "distclean",
                       "rust-analyzer", "modules_install", "install", "dtbs_install",
                       "menuconfig", "olddefconfig", "headers", "-k", "--jobs=64",
                       "O=/tmp", "ARCH=x86", "KCONFIG_CONFIG=/tmp/x", "../evil.o",
                       "fs/../../evil.o", "/abs/path.o", "./fs/exec.o", ".o", "fs/exec.c"):
            f.clear_log()
            result = f.run("build", source, target)
            assert f.log() == "", f"'{target}' reached make:\n{f.log()}"
            expect(result, 2, f"target {target!r}")

        # Output ownership: unmarked nonempty and foreign output are refused.
        unmarked = f.base / "unmarked"
        unmarked.mkdir()
        (unmarked / "stale").touch()
        expect(f.run("configure", source, output=unmarked), 1, "unmarked output")
        other = f.base / "other-linux"
        (other / "arch/arm64/configs").mkdir(parents=True)
        (other / "arch/arm64/configs/asahi.config").touch()
        expect(f.run("configure", str(other)), 1, "foreign output")
        expect(f.run("configure", source, output=f.source / "out"), 1, "output inside source")


def check_setup():
    with tempfile.TemporaryDirectory() as base:
        base = Path(base)
        lists = {"missing": base / "missing.txt", "empty": base / "empty.txt", "ok": base / "ok.txt"}
        lists["empty"].write_text("# only a comment\n\n")
        lists["ok"].write_text("clang  # compiler\nrust\n")

        def run(package_list, *args):
            stub = f"detect_host() {{ ID=arch; package_list={shlex.quote(str(package_list))}; }}"
            return subprocess.run(
                ["bash", "-c", f'source "$1"; shift; {stub}; main "$@"', "asahi-setup-check", str(SETUP), *args],
                env={"PATH": "/usr/bin:/bin"}, text=True, capture_output=True,
            )

        expect(run(lists["missing"], "--plan"), 1, "missing package list")
        expect(run(lists["empty"], "--plan"), 1, "empty package list")
        result = run(lists["ok"], "--plan")
        expect(result, 0, "package plan")
        assert result.stdout == "clang\nrust\n", result.stdout
        expect(run(lists["ok"], "--bogus"), 2, "invalid setup mode")


def main():
    check_wrapper()
    check_setup()
    print("PASS: Asahi build wrapper and setup fixtures")


if __name__ == "__main__":
    main()
