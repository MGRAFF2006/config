#!/usr/bin/env bash
# Optional system-wide fix (needs sudo). Survives alice-vision package overwrites of alicevision.sh.
set -euo pipefail
tee /etc/profile.d/alicevision-voctree.sh >/dev/null <<'EOF'
# Drop-in: alice-vision ships the tree but omits ALICEVISION_VOCTREE in alicevision.sh
export ALICEVISION_VOCTREE="${ALICEVISION_VOCTREE:-/usr/share/aliceVision/vlfeat_K80L3.SIFT.tree}"
EOF
chmod 644 /etc/profile.d/alicevision-voctree.sh
echo "Wrote /etc/profile.d/alicevision-voctree.sh"
