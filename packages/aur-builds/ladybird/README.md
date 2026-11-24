# Ladybird with Rust 1.99+

Local variant of AUR `ladybird 1:2026.47.7-1`, recipe commit
`7e0cad1` ("Retarget upstream releases"). The AUR recipe, its source pins
(tag `2026.47.7`, resolving to commit
`4e9acf4c02ca23239fe32224a303dcea4614562b`) and its two patches are kept
unchanged. Local release `1:2026.47.7-1.1` only adds `rust-1.99.patch`.

Rust 1.99 deprecated atomic `fetch_update` in favor of `try_update`.
Ladybird's CMake build passes `-Dwarnings` to its Rust crates, so the
deprecation fails the build. The 2026.47.7 tree has ten calls in eight files
(AK, LibJS, and LibWeb CSS, layout and Web Audio). The patch renames all ten
without changing their closures, memory ordering or result handling; warnings
remain errors. Rust documents the old method as an alias of the replacement:
[atomic API](https://doc.rust-lang.org/std/sync/atomic/struct.Atomic.html).

The epoch is the AUR's: its switch from date versions (`20261101`) to tagged
releases needed `epoch=1`, so `1:2026.47.7-1.1` is newer than the installed
`20261101-2.1` and the upgrade below does not downgrade. Packaging follows the
AUR recipe, which now installs under `/opt/ladybird`.

## Currently installed

The laptop runs `ladybird 20261101-2.1`, built on 2026-11-09 from the previous
version of this recipe (AUR `20261101-2` plus a four-call Rust patch). That
recipe is in Git history only; do not rebuild it, because the tagged
release supersedes it.

## Build and install

Use mains power, keep at least 10 GiB free, and limit parallelism to available
memory:

```bash
cd ~/Documents/config/packages/aur-builds/ladybird
SRCDEST="$HOME/.cache/yay/ladybird" \
  CMAKE_BUILD_PARALLEL_LEVEL=8 CARGO_BUILD_JOBS=4 makepkg -s
sudo pacman -U ./ladybird-1:2026.47.7-1.1-x86_64.pkg.tar.zst
pacman -Q ladybird
sudo pacman -Qkk ladybird
```

`makepkg` applies the patch in `prepare()`. Do not use `--noextract` on a
source tree that has not received it.

A plain AUR helper upgrade to a later `1:<version>-1` would replace this build
and drop the patch. Before upgrading, compare the new AUR recipe with this one:
port the patch again (keep the AUR epoch and use pkgrel `<n>.1`), or remove this
workaround once upstream no longer calls `fetch_update`. Check with
`git grep -n '\.fetch_update(' -- '*.rs'` in the new source.

The same applies to AUR updates that change only packaging and keep the
Ladybird version. pacman orders `1:2026.47.7-2` above this `1:2026.47.7-1.1`,
so the helper would install the AUR build without `rust-1.99.patch`. Port the
packaging change here and rebuild as `1:2026.47.7-2.1`, which sorts above the
AUR's `-2`.

## Recovery

The installed `ladybird-20261101-2.1-x86_64.pkg.tar.zst` and the earlier
`ladybird-20261004-1-x86_64.pkg.tar.zst` remain in `~/.cache/yay/ladybird/`.
If the new build misbehaves, reinstall one with `sudo pacman -U`; pacman
reports the intentional downgrade. The 2026-11-09 repair's original recipe and
AK source file are saved under `~/.local/state/ladybird-repair-2026-11-09/`,
alongside the build log. That state directory is machine-local and must stay
out of Git.

## Verification

### 2026-11-24 — `1:2026.47.7-1.1` recipe

Not built or installed. The patch applies with zero fuzz and no offsets to tag
`2026.47.7`, and the tree has no other `fetch_update` calls. The AUR's two
patches also apply without fuzz. All three patch checksums match the recipe.
With system Rust 1.100.0 and `RUSTFLAGS=-Dwarnings`,
`cargo check --workspace --all-targets` of the patched tree passed. Without
the patch, the same check failed with the `fetch_update` deprecation error in
AK. This checks the Rust workspace standalone, not the CMake-driven build.
A full `makepkg` build, installation and browser runtime are unverified.

### 2026-11-09 — `20261101-2.1` (installed)

The full `makepkg -ef` build succeeded on the laptop with system Rust 1.99.1,
including compilation of the Rust test workspace. All 37 `TestUtf16String`
cases passed, including ownership transfer and reference counting.

The installed package passed `pacman -Qkk` (188 files, none altered), and
`pacman -Dk` reported no database errors. A headless run of `/usr/bin/Ladybird`
with a temporary profile and separate XDG directories produced the expected
JavaScript-generated Unicode text after CSSOM mutation, computed-style and
node-cloning checks. The headless run logged a Fontconfig config-access warning,
although system `fc-match` succeeds and `/etc/fonts/fonts.conf` is readable.
A headless PNG rendered the expected text and styling despite that warning.
The native GUI and a fresh empty-cache build were not exercised.
