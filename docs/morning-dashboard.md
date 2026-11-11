# Private morning dashboard

URL: **https://homelab-dev.tail03caec.ts.net/morning/**

The dashboard and collectors run as humunkulud on homelab-dev, with user linger
already enabled. No laptop paths, browser sessions, tunnels or laptop process
are required. The existing morning collector runs at **04:50 Europe/Berlin**.
The separately managed T3 delivery runs at **05:00 Europe/Berlin** on homelab-dev;
its configuration is outside this implementation. Setup below changes neither schedule.

## Operation

The existing Node collector, Thunderbird bridge, university IMAP reader, `gh`,
private `agent-access.py` installation and authenticated Codex launcher remain
prerequisites. Mail/calendar require the existing central Thunderbird profile;
calendar ownership, dismissed assignments and other selections come from the
private `~/.local/state/agent-life/brief-preferences.txt`. Do not replace it.
The bridge is installed at `~/Projects/thunderbird-mcp/mcp-bridge.cjs` (or
`THUNDERBIRD_BRIDGE_PATH`). IMAP invokes the existing
`~/Documents/config/scripts/agent-access.py`; its vault is not part of this PR. The existing university vault item ID belongs
in private `~/.config/agent-life/university-imap-item-id` (0600), or
`UNIVERSITY_IMAP_ITEM_ID`; the existing value was provisioned on this host.

Deploy these task files to `~/Documents/config` on homelab-dev, then run:

```sh
scripts/setup-morning-dashboard.sh
systemctl --user start agent-morning-brief.service
```

Setup enables the dashboard service and adds only `/morning` to persistent
Tailscale Serve. Existing `/`, `/windows` and other handlers remain in place.
The Node server listens only on `127.0.0.1:8787`. The service is enabled under
`default.target`; existing `loginctl show-user humunkulud -p Linger` is `yes`,
so the user manager and dashboard start after boot without an interactive login.
Reboot was not performed during verification.

The report is synthesized with shell/tools/web disabled and the existing trusted
preferences. Source text is untrusted. Publication follows successful synthesis;
`latest-brief.md` and `dashboard.json` are replaced by rename, so a failed update
retains the previous dashboard edition. Refresh reloads the published edition
and current local service status; it does not recollect accounts or regenerate.
The page labels this as a morning edition, not a live agenda, and warns for
older editions. The report's coverage paragraph preserves upstream cache and
missing-account limitations.

## Garmin Personal API

Create a key at Garmin Connect's Personal API Key settings. The parent/user
must provision it privately in **`~/.config/agent-life/garmin-api-key`**, owned by
humunkulud, mode **0600**; keep its parent directory private (0700). Optional
`GARMIN_API_KEY` overrides the file for an explicitly configured service process.
Never put the key in source, a command argument, browser storage or a public
systemd environment file. Keep the key in the existing Garmin Bitwarden item as a hidden `personal-api-key` field, with a separate `personal-api-key-expires` field for renewal.

After provision, regenerate the brief. Keys and access tokens remain server-side;
tokens are exchanged per collection and never persisted. No Garmin password or
scraping is used. Missing keys leave the report functional with “Not connected”.
Expired keys, upstream failures, empty readings and per-endpoint failures have
explicit states. Missing values are null, not fabricated zeroes. Device sync may
lag collection. The UI shows the requested day, observation times where supplied,
per-endpoint collection times and recent activities. No health advice is generated.

Official documentation consulted 2026-11-11:

- [Personal API and token exchange](https://developer.garmin.com/gc-developer-program/personal/personal-api/)
- [Official OpenAPI schemas](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)

Requests use the documented Personal API host. Token POST uses `ApiKey` auth;
subsequent requests use the returned bearer token. The token endpoint returns
**plain text**, and rejects `Accept: application/json` with HTTP 406; do not
negotiate or parse JSON for token exchange. Data endpoints return JSON.
Live token exchange and all four data endpoints were verified on 2026-11-11.
The reviewed public OpenAPI v1.0.0 supplies these paths and fields:

| Resource | Request | Published fields |
| --- | --- | --- |
| Sleep | `/sleep-service/sleep/dailySleep?date=YYYY-MM-DD` | calendarDate, sleepTimeSeconds, sleepScores.overall.value, sleepEndTimestampGMT |
| Daily summary | `/usersummary-service/usersummary/daily?calendarDate=YYYY-MM-DD` | calendarDate, totalSteps, restingHeartRate, bodyBatteryMostRecentValue, wellnessEndTimeGmt |
| HRV | `/hrv-service/hrv/YYYY-MM-DD` | hrvSummary.calendarDate, hrvSummary.lastNightAvg, endTimestampGMT |
| Activities | `/activitylist-service/activities/search/activities?start=0&limit=5&sortOrder=desc` | activityName, startTimeGMT, duration, distance |

## Additional sources and privacy

The photo collector reads only a small allowlist from the private
`~/.local/state/agent-life/google-photos-migration.json`: verified/updated times,
backup verification, cleanup pause and existing change flags. It never changes
cloud data, resumes migration, deletes media or changes Google One. Checkpoint
status is not a new live cloud verification. Local health covers only four
homelab-dev user units, not other machines or the whole homelab. No weather is
added because a home location was not established.

The server serves three fixed assets and `/data`, not a directory. `/data`
contains the sanitized synthesized brief, selected Garmin readings, source
status/times, the photo projection and local unit status. Raw snapshots, mail,
partner calendars, prompts, logs, private preferences and credentials are never
served. The brief itself is private personal content: do not publish screenshots
or runtime JSON to GitHub. HTTP is read-only, cache-disabled, with restrictive
CSP, no external assets, no referrers, HTML escaping through DOM text nodes and
no arbitrary filesystem paths. Source links open with noreferrer/noopener;
signed query parameters and authentication paths are removed at publication.

Access is controlled by existing Tailscale ACLs and HTTPS, **not an application
login**: anyone permitted by the tailnet ACL to access this host's HTTPS can read
the page. Local same-user/root access is trusted. Tailscale Funnel is not used.

## Checks and recovery

```sh
node scripts/check-agent-life.cjs
node --test scripts/check-morning-dashboard.cjs
# Optional deployed UI check using an existing Playwright installation and Chromium:
# MORNING_PLAYWRIGHT_MODULE=/path/to/playwright MORNING_BROWSER=/usr/bin/chromium \
#   node scripts/check-morning-dashboard-ui.cjs
systemctl --user status agent-morning-dashboard.service agent-morning-brief.service
systemctl --user show agent-morning-brief.service -p Result -p ExecMainStatus
journalctl --user -u agent-morning-dashboard.service -n 30
systemctl --user restart agent-morning-dashboard.service
# Regenerate all sources and the dashboard (may use the existing Codex account):
systemctl --user start agent-morning-brief.service
# Or republish the existing successful report:
node scripts/agent-morning-dashboard.cjs publish
```

The private source baseline is retained at
`~/.local/state/agent-life/implementation-baseline-2026-11-11/`. To disable just
the dashboard, stop/disable `agent-morning-dashboard.service` and remove only its
Serve path with `tailscale serve --set-path=/morning off`. Do not disable all Serve
handlers. The existing morning timer and delivery schedule are independently owned.

Verified on homelab-dev: fresh report with photo backup/pause corrected, missing
Garmin explicit, all existing collectors successful; HTTPS page/data, old routes
preserved, user service enabled and linger enabled. Automated boundary checks
cover projection, credential exclusion, arbitrary-path rejection, method rejection,
failed-publication retention, Garmin endpoint contracts and partial/missing states.
Isolated headless Chromium checked actual deployed HTTPS at 1440×1100 and 390×844,
refresh, expanded coverage, no horizontal overflow, empty/stale/unavailable states,
unsafe markup and connection failure. Screenshots remain private under
`~/.local/state/agent-life/dashboard-verification/`.

This host's resolver did not resolve its own MagicDNS name during testing. HTTPS
was verified with the real hostname and certificate using the current verified
Tailscale address (`curl --resolve` / Chromium host resolver mapping), not by
bypassing TLS. Use `MORNING_TAILSCALE_IP` only with a freshly verified host address to repeat
that resolver workaround in the UI check. External laptop DNS/HTTPS and live Garmin collection were subsequently verified. Reboot remains untested.
