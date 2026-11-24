# Development VM worktree storage

The `dev-worktrees` ext4 filesystem is a 512 GiB virtual disk on Proxmox's
mirrored HDD pool. It mounts at `/srv/development`; its `worktrees` directory
bind-mounts at `/home/humunkulud/.t3/worktrees`. Existing T3 paths remain valid.
T3's database, runtime and ordinary `~/Projects` checkouts stay on the SSD.
The new disk is included in the VM's existing nightly backups.

After the disk is mounted and a verified worktree copy exists, install with:

```bash
bash scripts/install-homelab-dev-storage.sh
```

The installer requires the existing worktree path to be empty or already
mounted from this disk. It never formats a device, copies worktrees or removes
the original files. During the initial migration, T3 must be paused for the
final sync and cutover. Verify file contents and metadata before reclaiming
the original SSD copy. Keep an independently recoverable backup.

The user-service drop-in prevents T3 from starting if the worktree mount is
missing. Both system mounts are enabled for boot. To verify without a reboot:

```bash
systemctl is-enabled srv-development.mount home-humunkulud-.t3-worktrees.mount
findmnt --mountpoint /home/humunkulud/.t3/worktrees
systemctl --user status t3code.service
```

For recovery, stop T3, unmount the bind mount, restore the original worktrees
at their SSD path, and remove `~/.config/systemd/user/t3code.service.d/worktrees.conf`
before reloading and starting the user service. Only disable the two system
mount units after confirming the restored worktrees are on the SSD. The old
SSD copy is intentionally removed only after migration verification; later
recovery must use the HDD copy or a VM backup.
