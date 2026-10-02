#!/usr/bin/env bash
# Install AliceVision + Meshroom (develop, SYCL DepthMap) on desktop.
# Run inside tmux on desktop:  tmux new -s meshroom-install './install-meshroom-stack.sh'
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="${BUILD_ROOT:-$HOME/builds/meshroom-stack}"
PKGDEST="${PKGDEST:-$BUILD_ROOT/pkgs}"
LOG="$BUILD_ROOT/install.log"

mkdir -p "$BUILD_ROOT" "$PKGDEST"
exec > >(tee -a "$LOG") 2>&1

echo "==> $(date -Is) meshroom stack install starting"
echo "    ROOT=$ROOT"
echo "    BUILD_ROOT=$BUILD_ROOT"
echo "    host=$(tailscale status --self 2>/dev/null | awk 'NR==1{print $2}' || hostname)"

export MAKEFLAGS="${MAKEFLAGS:--j$(nproc)}"
export PKGDEST
export PACKAGER="${PACKAGER:-humunkulud <graff.mathis@gmail.com>}"

need_sudo() {
  if ! sudo -n true 2>/dev/null; then
    echo ""
    echo ">>> sudo password required (installing packages / deps)."
    echo ">>> Stay attached to this tmux session and enter it when prompted."
    echo ""
  fi
}

install_repo_makedeps() {
  need_sudo
  # Stale DBs cause 404s (e.g. old nvidia-utils); refresh first.
  sudo pacman -Syu --needed --noconfirm \
    eigen cmake git swig doxygen python-sphinx boost freetype2 flann expat \
    onnx base-devel \
    clang20 llvm20 llvm20-libs lld20 compiler-rt20 \
    qt6-charts qt6-3d pyside6 shiboken6 python-psutil
}

pkg_built() {
  local name="$1"
  local package
  for package in "$PKGDEST/${name}-"*.pkg.tar.zst; do
    [[ -f "$package" && "$package" != *-debug-* ]] && return 0
  done
  return 1
}

build_aur_pkg() {
  local name="$1"
  local dir="$ROOT/$name"
  [[ -d "$dir" ]] || { echo "missing $dir"; exit 1; }

  if ! pkg_built "$name"; then
    echo "==> Building $name"
    rm -rf "${BUILD_ROOT:?}/$name"
    cp -a "$dir" "$BUILD_ROOT/$name"
    cd "$BUILD_ROOT/$name"
    if command -v yay >/dev/null; then
      need_sudo
      dependency_names="$(bash -c 'source "$1"; printf "%s\n" "${makedepends[@]}" "${depends[@]}"' bash ./PKGBUILD)"
      mapfile -t dependencies < <(printf '%s\n' "$dependency_names" | sed '/^$/d' | sort -u)
      if ((${#dependencies[@]})); then
        yay -S --needed --noconfirm --asdeps "${dependencies[@]}"
      fi
    fi
    makepkg -sf --noconfirm --needed
    shopt -s nullglob
    local built=( ./*.pkg.tar.zst )
    if ((${#built[@]})); then
      cp -f "${built[@]}" "$PKGDEST/"
    fi
    pkg_built "$name" || { echo "ERROR: no package produced for $name"; exit 1; }
  else
    echo "==> Skipping build of $name (already in $PKGDEST)"
  fi

  # Install immediately so later packages can depend on it.
  need_sudo
  shopt -s nullglob
  local to_install=()
  local p
  for p in "$PKGDEST/${name}-"*.pkg.tar.zst; do
    [[ "$p" == *-debug-* ]] && continue
    to_install+=("$p")
  done
  echo "==> Installing ${to_install[*]}"
  sudo pacman -U --noconfirm --needed "${to_install[@]}"
}

install_pkgs() {
  need_sudo
  shopt -s nullglob
  # Skip debug packages; they are huge and unused at runtime.
  local pkgs=( "$PKGDEST"/*.pkg.tar.zst )
  local runtime=()
  local p
  for p in "${pkgs[@]}"; do
    [[ "$p" == *-debug-* ]] && continue
    runtime+=("$p")
  done
  [[ ${#runtime[@]} -gt 0 ]] || { echo "No packages in $PKGDEST"; exit 1; }
  echo "==> Installing: ${runtime[*]}"
  sudo pacman -U --noconfirm --needed "${runtime[@]}"
}

verify() {
  echo "==> Verify"
  pacman -Q adaptivecpp alice-vision meshroom
  compgen -G '/usr/lib/libaliceVision_depthMap_sycl.so*' >/dev/null || { echo 'Missing SYCL DepthMap library' >&2; exit 1; }
  [[ -s /usr/share/aliceVision/vlfeat_K80L3.SIFT.tree ]] || { echo 'Missing vocabulary tree' >&2; exit 1; }
  command -v meshroom aliceVision_depthMapEstimation
}

# Order matters
install_repo_makedeps
build_aur_pkg adaptivecpp
build_aur_pkg openmesh
build_aur_pkg python-pyseq
build_aur_pkg libe57format
# nanoflann/metis from AUR if not in repos on this machine
if ! pacman -Q nanoflann &>/dev/null; then
  if [[ -d "$ROOT/nanoflann" ]]; then build_aur_pkg nanoflann; else
    need_sudo; yay -S --needed --noconfirm nanoflann
  fi
fi
if ! pacman -Q metis &>/dev/null; then
  build_aur_pkg metis
fi
build_aur_pkg alice-vision
build_aur_pkg meshroom
install_pkgs
verify

echo "==> $(date -Is) done. Log: $LOG"
echo "    DepthMap tip: export ALICEVISION_DEPTHMAP_BACKEND=1"
echo "    Remote farm: see ../remote-farm/README.md"
