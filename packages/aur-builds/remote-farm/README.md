# Meshroom remote compute on `desktop` (AMD RX 7600 / SYCL)

AliceVision is **not** a standalone network service. Remote work is done by running
Meshroom compute workers (LocalFarm or SSH/`meshroom_compute`) on the machine that
has the GPU build.

## Prerequisites

1. Same stack installed on desktop (`alice-vision` with SYCL + `meshroom`).
2. Shared project path (Syncthing already syncs `~/Documents/Archive/Schuh`).
3. Same absolute paths on both machines (`/home/humunkulud/...`).

## Desktop session — Run Meshroom on desktop (simplest)

```bash
ssh desktop
# or Sunshine/Moonlight
cd ~/Documents/Archive/Schuh
export ALICEVISION_DEPTHMAP_BACKEND=1
export ALICEVISION_VOCTREE=/usr/share/aliceVision/vlfeat_K80L3.SIFT.tree
./proj/run_meshroom.sh
```

Use this for DepthMap / heavy nodes. Keep lighter nodes on the laptop if you want.

## LocalFarm

LocalFarm has not been validated with these package recipes. Do not depend on
it for deployment or recovery; use the desktop UI or SSH workflow below first.

## SSH compute — One-shot remote node via SSH

From the laptop, after SfM succeeds locally:

```bash
rsync -a ~/Documents/Archive/Schuh/ desktop:~/Documents/Archive/Schuh/
ssh desktop
tmux new -s meshroom-compute
export ALICEVISION_DEPTHMAP_BACKEND=1 ALICEVISION_VOCTREE=/usr/share/aliceVision/vlfeat_K80L3.SIFT.tree
meshroom_compute --node DepthMap_1 ~/Documents/Archive/Schuh/proj/schuh.mg
```

Use the actual node name from your project. Then sync cache back (or rely on Syncthing).

## Recommendation

Until LocalFarm is battle-tested on your packages: **install the stack on desktop,
run DepthMap there with the UI or SSH**. Wire LocalFarm after DepthMap works once.
