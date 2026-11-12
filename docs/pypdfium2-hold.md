# PDFium AUR upgrade hold

On 2026-11-09, `python-pypdfium2` 5.15.1-1 requires
`libpdfium.so=libpdfium.so-64`, which yay cannot resolve. The previous
`yay -Syu --ignore=python-pypdfium2` workaround applied to one invocation only.
The installed 5.14.0-1 bundles PDFium; import and a 72 × 72 PDF-page render pass.

The focused installer below backs up pacman's configuration, installs
`system/pacman/pypdfium2-hold.conf` under `/etc/pacman.d/`, and includes it in
the `[options]` section. Run it from this checkout:

```bash
bash scripts/install-pypdfium2-hold.sh --dry-run
bash scripts/install-pypdfium2-hold.sh
bash scripts/install-pypdfium2-hold.sh --check
```

Ordinary `yay` and pacman upgrades now honor the hold, including in existing
terminals and after reboot. All other packages remain eligible for upgrades.
This is a persistent workaround: pypdfium2 and its bundled PDFium receive no
updates while held. Recheck the
[AUR recipe](https://aur.archlinux.org/packages/python-pypdfium2) before lifting it.
Do not bypass dependency validation or substitute an unrelated library.

To lift the hold, remove the exact
`Include = /etc/pacman.d/pypdfium2-hold.conf` line from `/etc/pacman.conf` with
`sudoedit /etc/pacman.conf`, then remove `/etc/pacman.d/pypdfium2-hold.conf`.
Run `pacman-conf IgnorePkg` to verify the effective configuration, then use a
normal full `yay` upgrade. Other independently configured holds must remain.
