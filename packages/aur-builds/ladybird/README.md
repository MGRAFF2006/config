# Ladybird with Rust 1.99

Local variant of AUR `ladybird 20261101-2`, recipe commit
`30b02ea87e8d21c742acc6f2dbe8b8b077289cc6`.
The upstream source and existing three AUR patches remain pinned.
Local release `20261101-2.1` adds `rust-1.99.patch`.

Rust 1.99 deprecated atomic `fetch_update` in favor of `try_update`.
Ladybird treats Rust warnings as errors, so its AK crate fails to compile.
The same call also occurs in three CSS implementation files. The patch updates
all four calls without changing their closures or memory ordering; warnings
remain errors. Rust documents the old method as an alias of the replacement:
[atomic API](https://doc.rust-lang.org/std/sync/atomic/struct.Atomic.html).

## Build and install

Use mains power, keep at least 10 GiB free, and limit parallelism to available
memory. Reuse source downloads from yay if available:

```bash
cd ~/Documents/config/packages/aur-builds/ladybird
SRCDEST="$HOME/.cache/yay/ladybird" \
  CMAKE_BUILD_PARALLEL_LEVEL=8 CARGO_BUILD_JOBS=4 makepkg -s
sudo pacman -U ./ladybird-20261101-2.1-x86_64.pkg.tar.zst
pacman -Q ladybird
sudo pacman -Qkk ladybird
```

The first repaired build reused the configured `~/.cache/yay/ladybird/src`
tree. Its recipe and new patch were copied into the yay build directory, and
the patch was applied to the already prepared source before `makepkg -ef`.
An ordinary fresh build applies the patch in `prepare()`.
Do not use `--noextract` on a source tree that has not received the patch.

When refreshing from AUR, compare the recipe and source revision and remove
this workaround once upstream updates all affected calls. No package upgrade
hold is needed: a newer upstream package release supersedes the local release.

## Recovery

The previous `ladybird-20261004-1-x86_64.pkg.tar.zst` remains in
`~/.cache/yay/ladybird/`. Restore it with `sudo pacman -U` if necessary.
The 2026-11-09 repair's original recipe and AK source file are saved under
`~/.local/state/ladybird-repair-2026-11-09/`, alongside the build log.
That state directory is machine-local and must stay out of Git.

## Verification — 2026-11-09

The full `makepkg -ef` build succeeded on the laptop with system Rust 1.99.1,
including compilation of the Rust test workspace. The four-file patch applies
without fuzz to the pinned upstream sources. All 37 `TestUtf16String` cases
passed, including ownership transfer and reference counting.

The installed `20261101-2.1` package passed `pacman -Qkk` (188 files, none altered),
and `pacman -Dk` reported no database errors. A headless run of `/usr/bin/Ladybird`
with a temporary profile and separate XDG directories produced the expected
JavaScript-generated Unicode text after CSSOM mutation, computed-style and
node-cloning checks. The headless run logged a Fontconfig config-access warning,
although system `fc-match` succeeds and `/etc/fonts/fonts.conf` is readable.
A headless PNG rendered the expected text and styling despite that warning.
The native GUI and a fresh empty-cache build were not exercised.
