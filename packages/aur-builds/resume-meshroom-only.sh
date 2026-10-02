#!/usr/bin/env bash
# Resume Meshroom build after alice-vision is already installed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_ROOT="${BUILD_ROOT:-$HOME/builds/meshroom-stack}"
PKGDEST="${PKGDEST:-$BUILD_ROOT/pkgs}"
export PKGDEST MAKEFLAGS="${MAKEFLAGS:--j$(nproc)}"
install_cached() {
  local name="$1" package
  local archives=()
  for package in "$PKGDEST/${name}-"*.pkg.tar.zst; do
    [[ -f "$package" && "$package" != *-debug-* ]] && archives+=("$package")
  done
  ((${#archives[@]})) || { echo "Missing cached runtime package: $name" >&2; return 1; }
  sudo pacman -U --noconfirm --needed "${archives[@]}"
}
mkdir -p "$PKGDEST"

echo "==> Ensuring alice-vision is installed"
if ! pacman -Q alice-vision &>/dev/null; then
  install_cached alice-vision
fi

echo "==> Building meshroom"
rm -rf "${BUILD_ROOT:?}/meshroom"
cp -a "$ROOT/meshroom" "$BUILD_ROOT/meshroom"
cd "$BUILD_ROOT/meshroom"
makepkg -sf --noconfirm --needed
shopt -s nullglob
built=( ./*.pkg.tar.zst )
if ((${#built[@]})); then
  cp -f "${built[@]}" "$PKGDEST/"
fi
# packages may already be in PKGDEST via env
install_cached meshroom

echo "==> Verify"
pacman -Q adaptivecpp alice-vision meshroom
ls -lh /usr/lib/libaliceVision_depthMap_sycl.so*
ls -lh /usr/share/aliceVision/vlfeat_K80L3.SIFT.tree
grep -n VOCTREE /etc/profile.d/alicevision.sh
command -v meshroom aliceVision_depthMapEstimation
echo DONE
