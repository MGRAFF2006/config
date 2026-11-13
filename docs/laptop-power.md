# Laptop power defaults

Apply only on Tailscale host `laptop`, from the canonical `~/Documents/config`
checkout, with the updated `home/.local/bin/bt-a2dp-claim` deployed:

```sh
python scripts/configure-laptop-power.py
python scripts/configure-laptop-power.py --apply
```

The installer backs up the DMS settings and previous service states under
`~/.local/state/config/laptop-power/`. It uses the running DMS settings API and
its settings-file watcher, without restarting the desktop or changing system
files. Existing appearance and other plugins are preserved.

Normal operation:

- After 2 minutes idle, dim the internal panel to 20%, unless it is already darker.
- After 3 minutes, turn off displays (plus DMS's existing 5-second fade).
- After 5 minutes, lock.
- Suspend after 15 minutes on battery or 30 minutes on AC; lock before sleeping.
- After a manual lock, turn off displays after 20 seconds.
- Select Power Saver on battery and Balanced on AC.
- Closing the lid suspends; the existing Hyprland switch bindings turn only
  `eDP-1` off when closed and back on when opened.

Activity restores the brightness chosen before dimming. Changes made manually
while dimmed are preserved. A pending restore record in DMS plugin settings
recovers the brightness after a shell crash or backend reconnect. External
monitors are never dimmed by this plugin; DMS's normal display-off timeout
still applies to connected monitors.

The coffee-cup **Keep Awake** tile in Control Center bypasses idle dimming,
display-off, lock and suspend timers. Its **Stay awake with the lid closed**
option is enabled, so jobs can continue with the internal panel off. The detail
page offers a duration or **Until I turn it off**. Prefer a duration for bounded
jobs. Manual lock still works, including its post-lock display-off timeout.
Critical-battery policy is unchanged.

The old permanent `laptop-lid-awake.service` is disabled. A laptop-local unit
condition prevents old setup scripts from reactivating its inhibitor while
the new plugin is installed. Bluetooth audio claiming remains active, but a
laptop-only service environment override disables its automatic lid inhibitor;
the shared helper's default on other computers is unchanged. Reapply this
installer if a full desktop-layout reset removes the Control Center tile.

Verification:

```sh
python scripts/check-laptop-idle-dim.py
shellcheck home/.local/bin/bt-a2dp-claim
dms ipc call plugins status laptopIdleDim
dms ipc call inhibit status
systemd-inhibit --list
```

The QML check uses fake backlight/session services and exercises restoration,
manual changes, inhibitors, backend reconnect and restart recovery. It never
changes the physical display. A separate private Wayland check confirmed that
the actual idle notifier triggers dimming and private keyboard activity
restores brightness. Physical lid-close and suspend/resume remain manual checks.

To roll back, turn Keep Awake on during the migration, disable the
`laptopIdleDim` plugin, restore the backed-up `settings.json` and
`plugin_settings.json`, remove the two installer-owned unit drop-ins (or restore
their backed-up versions), then run `systemctl --user daemon-reload` and restart
`bt-a2dp-claim.service`. Restore the old lid service's enabled/running state
from `services.json`. Finally turn Keep Awake off. No reboot is needed.
