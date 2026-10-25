# Personal-file sync and Git projects

Use Syncthing for personal Documents, Downloads, Pictures, Music, Videos and
Calibre Library. Use Git for software projects and `~/Documents/config`.
Personal notes, reports, archived coursework, travel plans and CAD/media source
files remain suitable for Syncthing, including personal documents that happen
to have a local Git repository. The setup does not infer software from `.git`
or exclude broad names such as `build`, `target` or `*.pdf`.

From this config checkout, with the local Syncthing daemon running:

```bash
python3 scripts/configure-personal-sync.py          # read-only preview
python3 scripts/configure-personal-sync.py --apply
```

The policy in `syncthing/personal-files.json` removes any existing folder
registration at or below Projects, config, and the identified standalone
software checkouts inside Documents. Personal parent folders remain registered,
with rooted exclusions for software children. Generated dependency, Python,
notebook, Gradle, Meshroom and video-processing caches are ignored; their local
files remain. Current device-specific ignore rules are preserved after the
managed block. Managed exclusions come first so an older inclusion rule cannot
reintroduce software or caches. Reapplying the same policy is a no-op.

This is a scope migration, not enrollment: it preserves existing peer sharing
and folder directions and creates no personal shares. The GUI API must use this
kit's local `http://127.0.0.1:8384` endpoint; its key is read from local Syncthing
state and never written to the repository. No daemon restart is needed.

Before changing anything, setup saves the removed registrations and original
ignore rules in a protected directory under `${XDG_STATE_HOME:-~/.local/state}/config/`.
The printed restore command uses `--restore /exact/backup/scope.json`.
Restoration is bound to the original device and refuses to overwrite folder
configuration or ignore rules changed since the backup. A backup is also usable
after partial application failure. Restoring registrations resumes their scans
and sharing; it is an intentional return to the old scope.

Apply on each reachable machine. An offline workstation retains its existing
registrations until this setup is run there after fetching the Git change.
Never enable legacy config-share pairing again when restoring this setup.

Git remotes protect committed, pushed work, not dirty files, untracked source,
ignored app databases or credentials. Keep those local and include needed
application data in an appropriate backup. Do not bulk-commit a working tree
just to replace Syncthing. If a laptop repository has an unborn or unrelated
history, connecting and fetching its existing remote is safe; checking out or
merging that history needs a separate comparison against the preserved local
files. Project-specific development and publication holds still apply.
