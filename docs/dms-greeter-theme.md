# Match the DMS login screen to the desktop

The laptop uses greetd with the standalone DMS greeter. Its per-account cache
can override the shared theme, so linking only the shared settings is not enough.
The 2026-11-05 repair replaces the old account snapshots with native live links
and keeps settings, session/wallpaper data and generated colors readable after
DMS replaces files atomically.

From an existing Hyprland/DMS 2.0 session:

```bash
python3 scripts/install-dms-greeter-theme.py
python3 scripts/install-dms-greeter-theme.py --apply
dms-greeter status
```

The installer requires an existing greeter-group membership and the managed
Hyprland greeter in `/etc/greetd/config.toml`. It prints a root-only backup under
`/var/backups/config-dms-greeter-theme/`. It preserves all greetd options,
including the terminal, account, remembered-session policy and any initial
session. It does not change PAM, enable another display manager or restart
greetd. The appearance takes effect at the next normal login screen.

The existing `dms-greeter-settings-permissions.service` now keeps a Gio directory
monitor running and uses the native `dms-greeter sync --profile --yes` command at
user startup and when settings, session or colors change. Events remain queued
while sync runs, including rapid replacements that a one-shot path unit misses.
It repairs inherited ACL masks after mode-0600 file
replacements and follows new wallpaper paths. Native profile sync grants the
greeter read access to DMS configuration, state/cache and the selected wallpaper.
It does not run the full sync command, which also rewrites greetd and reconciles
authentication. Keep the existing unit names so older setup flows remain compatible.

The greeter's separate Hyprland session loads a root-owned copy of the desktop's
`dms/expressive.lua`. Desktop autostarts, keybindings and services are excluded.
Reapply after intentionally changing that compositor fragment. The normal greeter
Lua installer also installs this fragment for new setups.
The greeter draws wallpaper and controls in one fullscreen layer: its native
wallpaper blur and translucent surfaces remain renderer effects. Loading the
desktop fragment does not create per-control acrylic blur inside that layer.

The installed greeter 2.0.0 renderer omitted fixed-radius settings and hardcoded
opaque popup surfaces. A small patch adds those settings through its existing
Shape API. `/usr/local/libexec/config-dms-greeter.py` validates the installed
binary and every staged UI file before using the root-owned copy under
`/usr/local/share/config-dms-greeter-ui`. Unknown package builds or modified UI
files launch the packaged UI instead. Colors/wallpaper still sync; the two visual
extensions require reviewing and updating the patch for a changed package.
Package files are never modified.

After a native **full** greeter sync or replacing greetd's command, reapply this
installer to retain the guarded renderer. Prefer profile-only sync for theme work.

The optional-session installer, `install-hyprland-dms.sh --with-greeter`, includes
this repair when DMS has generated its session and theme inputs. On a fresh
installation it enables synchronization and prints the post-login theme-install
command; the packaged renderer is used until its reviewed UI has been extracted.
Add `--with-appearance` to apply the saved desktop and app
palette too; ordinary reinstalls preserve the selected appearance:

```bash
bash scripts/install-hyprland-dms.sh laptop --with-appearance --with-greeter --dry-run
```

`--with-greeter` retains its existing, explicit PAM/setup scope. Use the dedicated
theme installer above when only appearance needs repair. The desktop appearance
preset also selects Breeze when DMS previously used an unspecified system cursor;
explicit custom themes, cursor sizes and hide preferences are preserved.

Verification:

```bash
python3 scripts/check-dms-greeter-theme.py
python3 scripts/check-dms-greeter-ui.py
python3 scripts/check-dms-greeter-watch.py
python3 scripts/check-desktop-appearance.py
systemctl --user status dms-greeter-settings-permissions.path
```

To return to the previous login appearance, disable the path and service, then
restore `etc/greetd/` from the printed backup. The unused root-owned UI can remain.
The backup also contains the previous shared links, account snapshot and ACLs;
move the current account-slot directory aside before restoring an old snapshot
so copying cannot follow live links into desktop settings. Restore saved ACLs
with `sudo setfacl --restore=BACKUP/permissions.acl` only when undoing the native
sharing changes too. A fresh login/logout is a separate verification from
rendering the greeter in a private nested compositor.
