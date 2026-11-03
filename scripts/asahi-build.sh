#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: asahi-build.sh doctor|configure|build SOURCE [make targets...]

doctor     Check the native Rust/LLVM tools against this kernel.
configure  Generate ARM64 defconfig plus the Asahi configuration fragment.
build      Build Image, modules and device trees, or the specified targets.

ASAHI_OUTPUT sets the output directory (default: ~/.cache/asahi-linux/build).
ASAHI_JOBS sets parallel jobs (default: 4). Outputs stay outside the source tree.
EOF
}

if [[ ${1:-} == --help ]]; then usage; exit 0; fi
if [[ $# -lt 2 ]]; then usage >&2; exit 2; fi
action=$1
source_dir=$(realpath -e -- "$2")
shift 2
case "$action" in doctor|configure|build) ;; *) usage >&2; exit 2 ;; esac
[[ -f "$source_dir/arch/arm64/configs/asahi.config" ]] || {
  echo "Not an Asahi kernel source tree: $source_dir" >&2; exit 1;
}

# shellcheck source=/dev/null
source /etc/os-release
case "$ID" in
  arch) llvm=1 ;;
  debian)
    [[ $VERSION_ID == 13 ]] || { echo "This toolchain targets Debian 13." >&2; exit 1; }
    llvm=-19
    ;;
  *) echo "Supported hosts: Arch Linux and Debian 13." >&2; exit 1 ;;
esac

# Explicit paths keep rustup/mise defaults for other projects unchanged.
rustc=/usr/bin/rustc
bindgen=/usr/bin/bindgen
[[ -x $rustc && -x $bindgen ]] || {
  echo "Run scripts/setup-asahi-build.sh --install first." >&2; exit 1;
}
sysroot=$("$rustc" --print sysroot)
rust_source="$sysroot/lib/rustlib/src/rust/library"
if [[ ! -f "$rust_source/core/src/lib.rs" && $ID == debian ]]; then
  # Ask the matching distribution package instead of guessing its source path.
  core_source=$(dpkg-query -L rust-src | awk '/\/library\/core\/src\/lib.rs$/ && !found {print; found=1}')
  rust_source=${core_source%/core/src/lib.rs}
fi
[[ -f "$rust_source/core/src/lib.rs" ]] || {
  echo "Matching Rust source is missing: $rust_source" >&2; exit 1;
}

output=${ASAHI_OUTPUT:-${XDG_CACHE_HOME:-$HOME/.cache}/asahi-linux/build}
mkdir -p -- "$output"
output=$(realpath -e -- "$output")
case "$output/" in
  "$source_dir/"*) echo "Use an output directory outside the source tree." >&2; exit 1 ;;
esac
if [[ -f "$output/.asahi-source" && $(cat "$output/.asahi-source") != "$source_dir" ]]; then
  echo "Output belongs to another source tree; choose a different ASAHI_OUTPUT." >&2
  exit 1
fi
printf '%s\n' "$source_dir" > "$output/.asahi-source"
kernel_make=(make -C "$source_dir" "O=$output" ARCH=arm64 "LLVM=$llvm"
  "RUSTC=$rustc" "BINDGEN=$bindgen" "RUST_LIB_SRC=$rust_source")

case "$action" in
  doctor)
    "$rustc" --version
    "$bindgen" --version
    "${kernel_make[@]}" rustavailable
    ;;
  configure)
    "${kernel_make[@]}" rustavailable
    "${kernel_make[@]}" defconfig asahi.config
    # A missing toolchain must never silently drop the Asahi GPU driver.
    for symbol in RUST ARM64_16K_PAGES; do
      grep -qx "CONFIG_$symbol=y" "$output/.config" || {
        echo "Required option CONFIG_$symbol is disabled." >&2; exit 1;
      }
    done
    grep -Eq '^CONFIG_DRM_ASAHI=[ym]$' "$output/.config" || {
      echo "The Asahi GPU driver is disabled." >&2; exit 1;
    }
    ;;
  build)
    [[ -f "$output/.config" ]] || { echo "Run configure first." >&2; exit 1; }
    jobs=${ASAHI_JOBS:-4}
    [[ $jobs =~ ^[1-9][0-9]*$ ]] || { echo "ASAHI_JOBS must be positive." >&2; exit 2; }
    available_kib=$(df -Pk -- "$output" | awk 'END {print $4}')
    if ((available_kib < 10 * 1024 * 1024)); then
      echo "Build refused: retain at least 10 GiB free on the output filesystem." >&2
      exit 1
    fi
    if (($# == 0)); then set -- Image modules dtbs; fi
    "${kernel_make[@]}" "-j$jobs" "$@"
    ;;
esac
