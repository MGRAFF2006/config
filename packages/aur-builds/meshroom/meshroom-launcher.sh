#!/bin/sh
export QSG_RENDER_LOOP="${QSG_RENDER_LOOP:-basic}"
export QT3D_MAX_THREAD_COUNT="${QT3D_MAX_THREAD_COUNT:-1}"
export ALICEVISION_ROOT="${ALICEVISION_ROOT:-/usr}"
export ALICEVISION_SENSOR_DB="${ALICEVISION_SENSOR_DB:-/usr/share/aliceVision/cameraSensors.db}"
export ALICEVISION_VOCTREE="${ALICEVISION_VOCTREE:-/usr/share/aliceVision/vlfeat_K80L3.SIFT.tree}"
# Prefer SYCL DepthMap on AMD when the library is present.
if [ -z "${ALICEVISION_DEPTHMAP_BACKEND:-}" ] && [ -e /usr/lib/libaliceVision_depthMap_sycl.so ]; then
  export ALICEVISION_DEPTHMAP_BACKEND=1
fi
exec /usr/lib/meshroom/meshroom-ui "$@"
