# Asahi kernel builds on laptop and homelab-dev

The source checkout and build outputs are independent on each machine. Transfer
commits through Git; do not sync dirty trees or credentials. These tools only
cross-compile ARM64 code. They do not install a kernel or modify the boot setup.

## Install and verify

From this config checkout:

```bash
bash scripts/setup-asahi-build.sh --plan
bash scripts/setup-asahi-build.sh --install
bash scripts/setup-asahi-build.sh --check
```

The focused installer uses the existing package-list convention. It supports
Arch Linux and Debian 13, installs no desktop components and changes no services.
Arch uses the current synchronized package database without a separate refresh;
perform a normal full system upgrade first if the host is behind that database.

Builds explicitly select distribution `/usr/bin/rustc`, matching `rust-src` and
`bindgen`. Debian uses LLVM 19; Arch uses its distribution LLVM. Existing rustup
and mise defaults are preserved. `doctor` checks compatibility against the actual
kernel, rather than assuming that installed version numbers are sufficient.

## Get the experiment

The review PR is within the personal fork:
<https://github.com/MGRAFF2006/linux/pull/1>.

For a new checkout:

```bash
git clone --single-branch --branch t3/asahi-update-7.2.15 \
  https://github.com/MGRAFF2006/linux.git ~/Projects/asahi-linux
```

Reuse an existing kernel object database when practical. Inspect its worktree
first and preserve unfinished checkouts or dirty work; a separate Git worktree
can share objects without replacing the original checkout.

On homelab-dev, `~/Projects/asahi-linux` resolves to
`/srv/development/projects/asahi-linux` on the development disk.
`~/.cache/asahi-linux` resolves to `/srv/development/build/asahi-linux` there,
so the default build output also stays off the root filesystem. The source
branch is `experiment/asahi-7.2.15`, at the same commit as the fork PR.

## Configure and build

```bash
cd ~/Documents/config
bash scripts/asahi-build.sh doctor ~/Projects/asahi-linux
bash scripts/asahi-build.sh configure ~/Projects/asahi-linux
bash scripts/asahi-build.sh build ~/Projects/asahi-linux
```

Set `ASAHI_OUTPUT` for a different output directory and `ASAHI_JOBS` for parallel
jobs. The default is four jobs and `~/.cache/asahi-linux/build`. Use a separate
output directory for each source worktree. The build command refuses to start
with less than 10 GiB free. Allow additional space for outputs; this guard is
not a quota or a guarantee against exhausting a filesystem during a build.

To compile only the C files changed by the 7.2.15 update:

```bash
bash scripts/asahi-build.sh build ~/Projects/asahi-linux \
  fs/exec.o kernel/fork.o net/core/skbuff.o net/bluetooth/hci_event.o \
  drivers/iio/light/hid-sensor-als.o \
  drivers/platform/cznic/turris-omnia-mcu-base.o \
  fs/smb/server/server.o fs/smb/smbdirect/accept.o \
  fs/smb/smbdirect/connection.o fs/smb/smbdirect/listen.o \
  fs/smb/smbdirect/socket.o
```

On homelab-dev, start a long build in a named remote tmux session so it survives
SSH disconnection and laptop sleep:

```bash
ssh homelab-dev
tmux new -s asahi-build
cd ~/Documents/config
set -o pipefail
bash scripts/asahi-build.sh build ~/Projects/asahi-linux 2>&1 | tee ~/.cache/asahi-linux/build.log
echo "Build exit status: $?"
```

Detach with Ctrl-B, D; reconnect with `tmux attach -t asahi-build`.
Artifacts are `arch/arm64/boot/Image`, device trees below `arch/arm64/boot/dts/`,
and module `.ko` files inside the output directory. Hardware boot, graphics,
keyboard, suspend/resume and networking tests remain separate from compilation.

## Verified result — 2026-11-03

The experiment at `58542935ba8be69599aaed5f785b551099a86ab2` passed the complete
`Image modules dtbs` build on homelab-dev with LLVM 19.1.7, Rust 1.85.1 and
bindgen 0.71.1. The resulting release is `7.2.15-g58542935ba8b`; the kernel
Image, Apple GPU/AOP/PMP/SEP modules and 110 Apple device-tree blobs were checked
for the expected format/architecture. Rebuilding `kernel/fork.o` reused the
existing object unchanged. The existing global Rust 1.99.0 default was preserved.

The laptop passed all eleven changed C objects and the Asahi Rust GPU object
with LLVM 23.1.4 and Rust 1.99.1. Its full kernel build was not run.
Debian's Rust 1.85.1 emits one nonfatal warning about the existing
`unnecessary_transmutes` lint attribute in unchanged `float.rs:59`.
No kernel was installed and no Apple hardware boot/runtime test was performed.
