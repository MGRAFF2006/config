# PDFium AUR upgrade hold

On 2026-11-09, `python-pypdfium2` 5.15.1-1 requires
`libpdfium.so=libpdfium.so-64`, which yay cannot resolve. The previous
`yay -Syu --ignore=python-pypdfium2` workaround applied to one invocation only.
The installed 5.14.0-1 bundles PDFium; import and a 72 × 72 PDF-page render pass.

## Apply

The installer only copies `system/pacman/pypdfium2-hold.conf` to
`/etc/pacman.d/pypdfium2-hold.conf`. It refuses a directory or symlink at that
path and backs up a differing regular file under
`/var/backups/config-pypdfium2-hold/`. It never edits `/etc/pacman.conf`; it
prints the one line to add there by hand. Run it from this checkout:

```bash
bash scripts/install-pypdfium2-hold.sh --dry-run
bash scripts/install-pypdfium2-hold.sh
```

Unless the installer reports that pacman already includes the drop-in, add this
line once, directly below the `[options]` header, not in a repository section
such as `[core]` (check first with `grep -n pypdfium2-hold /etc/pacman.conf`):

```ini
Include = /etc/pacman.d/pypdfium2-hold.conf
```

Edit with `sudoedit /etc/pacman.conf`. If `/etc/pacman.conf` is a symlink,
`sudoedit` refuses it; edit the target printed by the installer
(`readlink -f /etc/pacman.conf`) instead.

## Check

```bash
bash scripts/install-pypdfium2-hold.sh --check
```

The check is read-only and lets pacman interpret the configuration. It passes
only when the drop-in matches this repository, `pacman-conf IgnorePkg` reports
`python-pypdfium2` without warnings about the drop-in, and the hold disappears
when the `Include` line for the drop-in is left out. A misplaced include, a
repository glob such as `Include = /etc/pacman.d/*.conf` that also reads the
drop-in, or an unrelated literal `IgnorePkg = python-pypdfium2` therefore
fails the check. An `[options]` glob that includes the drop-in also fails; use
the exact line above. A separate wildcard hold such as `python-pypdfium?` is
not detected; it holds the package as well.

Ordinary `yay` and pacman upgrades then honor the hold, including in existing
terminals and after reboot. All other packages remain eligible for upgrades.
This is a persistent workaround: pypdfium2 and its bundled PDFium receive no
updates while held. Recheck the
[AUR recipe](https://aur.archlinux.org/packages/python-pypdfium2) before lifting it.
Do not bypass dependency validation or substitute an unrelated library.

## Remove

Delete the drop-in only after nothing includes it any more; pacman refuses to
run while an `Include` points at a missing file.

1. Find every reference, including ones in other included files:
   `grep -rn pypdfium2-hold /etc/pacman.conf /etc/pacman.d/`. Remove each
   `Include` line for the drop-in with `sudoedit` (on `/etc/pacman.conf` or its
   resolved target, as above).
2. Check before deleting: `pacman-conf IgnorePkg` must succeed and no longer
   list `python-pypdfium2`. If it still does, a reference or another hold
   remains; fix that first. Other independently configured holds must remain.
3. `sudo rm /etc/pacman.d/pypdfium2-hold.conf`, then run `pacman-conf >/dev/null`.
   If it reports the missing file, restore it with
   `sudo install -m 644 system/pacman/pypdfium2-hold.conf /etc/pacman.d/`
   from this checkout and repeat step 1.
4. Use a normal full `yay` upgrade.
