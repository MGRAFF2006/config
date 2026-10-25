# Laptop background load

Apply from the config checkout while Syncthing is running:

```bash
bash scripts/setup-laptop-sync.sh
```

This laptop-only setup uses Syncthing's authenticated local CLI to limit
I/O-intensive folder operations to one folder at a time and hashing to one
worker per existing folder. Syncthing persists the settings itself. There is
no service restart, CPU frequency change, file exclusion, or sync pause.
Large scans and catch-up syncs may take longer. Filesystem watching and the
hourly fallback scans remain enabled. New folders retain Syncthing's defaults;
rerun the script after adding folders if they should use the same tuning.

Before applying, the script saves a credential-free restore script under
`${XDG_STATE_HOME:-~/.local/state}/config/` and prints its exact path. Run it
with Bash to restore that invocation's prior values. Reapplying saves a new
backup of the current settings, so keep the first backup to undo the tuning.

Observed on 2026-10-25: Lenovo IdeaPad Slim 5 14AKP10, Ryzen AI 7 350,
Arch Linux 7.2.11. Power-saver mode, firmware low-power profile and the CPU's
power-saving preference were already active. CPU temperature was about
43–45 °C on battery during sampling; no fan RPM sensor was exposed.

Syncthing tracked roughly 1.85 million files / 170 GB in Projects and about
98,000 files / 60 GB in Documents, with hourly full scans. Its logs showed
retries hashing changing Git pack files. Its average CPU use since startup
was around 28% of one logical CPU, but a later 15-second sample measured
0.07%, so the scan load is intermittent. File search was also idle in that
sample; browser activity remained. These observations identify potential
background load, not a verified cause of every fan burst or a measured noise
improvement. Compare future scan bursts under similar conditions before
claiming an improvement.

The concurrency controls are documented in
[Syncthing's tuning guide](https://docs.syncthing.net/users/tuning.html).
