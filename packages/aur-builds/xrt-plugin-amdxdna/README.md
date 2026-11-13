# XDNA plugin for Arch XRT 2.25

On 2026-11-13 Arch provided `xrt 1:2.25.0-2` alongside
`xrt-plugin-amdxdna 1:2.21.75-2`. The plugin could not load:

```text
/usr/lib/libxrt_driver_xdna.so.2: undefined symbol: _ZN8xrt_core7elf_int18get_partition_sizeERKN3xrt3elfE
```

`xrt-smi examine` therefore reported zero devices even though the kernel had
loaded `amdxdna`, `/dev/accel/accel0` existed, and `flm validate` found the NPU.

This recipe rebuilds the userspace plugin from AMD's XRT 2.25 update
[`eb910d4`](https://github.com/amd/xdna-driver/commit/eb910d4da18ac87115e3ec6263fbb379600c23ac)
using the source headers for the exact installed XRT release
[`3923b2b`](https://github.com/Xilinx/XRT/commit/3923b2b5be55dfea72dee3c49d5cf13c02eda25a).
It links to Arch's installed XRT libraries. The small CMake file builds the
upstream plugin sources without rebuilding XRT or installing kernel modules,
firmware, or copies of XRT. No upstream C++ source patch is required.

## Build and install

From this directory, with Arch's `base-devel` installed:

```sh
makepkg -s
sudo pacman -U ./xrt-plugin-amdxdna-1:2.25.0.r20260624-1-x86_64.pkg.tar.zst
```

Git sources are pinned to full commit IDs. `CMakeLists.txt` has a SHA-256
checksum. The replacement keeps the original package name so pacman owns all
installed files. Its version is newer than the broken repository plugin.

The package requires exactly `xrt=1:2.25.0`: the plugin uses internal C++ APIs
that can change without changing the shared-library major version. A later XRT
update may be blocked until this recipe is rebuilt against that release or a
compatible official plugin replaces it. Do not bypass this dependency with
`--nodeps`.

## Verify

`xrt-smi examine` itself needs a sufficient memory-lock limit on this device.
With the local NPU setup installed, run it in a transient service:

```sh
sudo systemd-run --wait --pipe --collect --unit=npu-xrt-validation \
  -p User="$USER" -p LimitMEMLOCK=infinity /usr/bin/xrt-smi examine
```

Then exercise actual FastFlowLM inference through the local NPU service. A
passing `flm validate` alone does not demonstrate that XRT or model execution
works.

## Recovery

The original repository package remains in `/var/cache/pacman/pkg/`. It can be
restored with `sudo pacman -U` if needed, although the recorded version remains
incompatible with XRT 2.25. To return to the repository once a compatible
replacement is published, install the matching XRT and XDNA plugin together;
`pacman -S xrt xrt-plugin-amdxdna` explicitly selects those repository packages.
No global package-ignore rule is installed.
