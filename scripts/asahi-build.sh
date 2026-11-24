#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: asahi-build.sh doctor|configure|build SOURCE [build targets...]

doctor     Check the native Rust/LLVM tools against this kernel.
configure  Generate ARM64 defconfig plus the Asahi configuration fragment.
build      Build Image, modules and device trees, or the given targets:
           Image, Image.gz, modules, dtbs, or single files below the source
           tree ending in .o, .ko, .s, .i or .lst. Anything else is refused.

ASAHI_OUTPUT sets the output directory (default: ~/.cache/asahi-linux/build).
ASAHI_JOBS sets parallel jobs (default: 4). Outputs stay outside the source tree.
Make runs with a cleared environment (PATH, HOME and LANG only), so variables
such as KCONFIG_CONFIG or MAKEFLAGS cannot change the configuration or targets.
EOF
}

# Sets llvm, rustc, bindgen and rust_source for this host's distribution tools.
detect_toolchain() {
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
  local sysroot core_source
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
}

# A missing toolchain must never silently drop the Asahi GPU driver.
check_config() {
  local config=$1 symbol
  for symbol in RUST ARM64_16K_PAGES; do
    grep -qx "CONFIG_$symbol=y" "$config" || {
      echo "Required option CONFIG_$symbol is disabled; rerun configure." >&2; exit 1;
    }
  done
  grep -Eq '^CONFIG_DRM_ASAHI=[ym]$' "$config" || {
    echo "The Asahi GPU driver is disabled; rerun configure." >&2; exit 1;
  }
}

# Single-file targets: path segments below the source tree (no "." or ".."
# segments, no absolute paths) ending in an object, module or listing suffix.
single_target='^([A-Za-z0-9_][A-Za-z0-9_+.-]*/)*[A-Za-z0-9_][A-Za-z0-9_+.-]*\.(o|ko|s|i|lst)$'

check_target() {
  case "$1" in
    Image|Image.gz|modules|dtbs) return 0 ;;
  esac
  [[ $1 =~ $single_target ]] && return 0
  echo "Refusing make target '$1'." >&2
  echo "Allowed: Image, Image.gz, modules, dtbs, or SOURCE-relative .o/.ko/.s/.i/.lst files." >&2
  exit 2
}

main() {
  if [[ ${1:-} == --help ]]; then usage; exit 0; fi
  if [[ $# -lt 2 ]]; then usage >&2; exit 2; fi
  local action=$1
  source_dir=$(realpath -e -- "$2")
  shift 2
  case "$action" in doctor|configure|build) ;; *) usage >&2; exit 2 ;; esac
  [[ -f "$source_dir/arch/arm64/configs/asahi.config" ]] || {
    echo "Not an Asahi kernel source tree: $source_dir" >&2; exit 1;
  }
  if [[ $action == build ]]; then
    local target
    for target in "$@"; do check_target "$target"; done
  fi

  detect_toolchain

  output=${ASAHI_OUTPUT:-${XDG_CACHE_HOME:-$HOME/.cache}/asahi-linux/build}
  mkdir -p -- "$output"
  output=$(realpath -e -- "$output")
  case "$output/" in
    "$source_dir/"*) echo "Use an output directory outside the source tree." >&2; exit 1 ;;
  esac
  # Claim the output directory for one source tree. Existing output without an
  # owner marker may belong to another tree, so only an empty directory is claimed.
  # The marker appears atomically with its content: a hard link fails if another
  # run claimed the directory first, and that run's owner is then compared below.
  local marker="$output/.asahi-source" claim
  if [[ ! -e $marker ]]; then
    if [[ -n $(find "$output" -mindepth 1 -maxdepth 1 -print -quit) ]]; then
      echo "Output directory is not empty and has no owner marker: $output" >&2
      echo "Choose an empty or new ASAHI_OUTPUT." >&2
      exit 1
    fi
    claim=$(mktemp "$output/.asahi-claim.XXXXXX")
    printf '%s\n' "$source_dir" > "$claim"
    ln -- "$claim" "$marker" 2>/dev/null || true
    rm -f -- "$claim"
  fi
  if [[ $(cat -- "$marker" 2>/dev/null) != "$source_dir" ]]; then
    echo "Output belongs to another source tree; choose a different ASAHI_OUTPUT." >&2
    exit 1
  fi

  # A cleared environment keeps KCONFIG_CONFIG, MAKEFLAGS, ARCH, CROSS_COMPILE
  # and similar caller variables from changing the config file or the build.
  # Kbuild then uses its default $output/.config, the file checked below.
  local kernel_make=(env -i "PATH=$PATH" "HOME=$HOME" "LANG=${LANG:-C.UTF-8}"
    make -C "$source_dir" "O=$output" ARCH=arm64 "LLVM=$llvm"
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
      check_config "$output/.config"
      ;;
    build)
      [[ -f "$output/.config" ]] || { echo "Run configure first." >&2; exit 1; }
      local jobs=${ASAHI_JOBS:-4} available_kib
      [[ $jobs =~ ^[1-9][0-9]*$ ]] || { echo "ASAHI_JOBS must be positive." >&2; exit 2; }
      available_kib=$(df -Pk -- "$output" | awk 'END {print $4}')
      if ((available_kib < 10 * 1024 * 1024)); then
        echo "Build refused: retain at least 10 GiB free on the output filesystem." >&2
        exit 1
      fi
      # Kbuild resyncs the config when Kconfig inputs or the toolchain changed,
      # which can drop Rust and the GPU driver. Resync now with the same tools
      # and check the effective result before anything is compiled.
      "${kernel_make[@]}" syncconfig
      check_config "$output/include/config/auto.conf"
      if (($# == 0)); then set -- Image modules dtbs; fi
      "${kernel_make[@]}" "-j$jobs" "$@"
      ;;
  esac
}

# Run only when executed; the regression check sources this file to stub
# detect_toolchain on hosts without the distribution Rust toolchain.
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
  main "$@"
fi
