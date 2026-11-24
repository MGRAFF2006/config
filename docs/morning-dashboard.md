# Private morning dashboard

URL: **https://homelab-dev.tail03caec.ts.net/morning/**

The dashboard and collectors run as humunkulud on homelab-dev, with user linger
already enabled. No laptop paths, browser sessions, tunnels or laptop process
are required. The existing morning collector runs at **07:00 Europe/Berlin**.
The separately managed T3 delivery runs at **07:10 Europe/Berlin** on homelab-dev;
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

## Calendar workspace and daily edition

The responsive dashboard opens on the current Berlin date independently of the
published edition date. Week/month views have previous, next, Today and go-to-date
controls. Selecting a day reveals every matching entry, including simultaneous
and all-day events. The calendar occupies most desktop width; a narrow adjacent
rail holds the short daily synthesis and selected-day agenda. Mobile places the
calendar before the daily brief. Category filters distinguish own, club, study,
shared context and recorded Garmin activity. Shared partner context is explicitly
not attendance; unconfirmed ownership and optional/unconfirmed dates remain labelled.

Calendar collection reads the previous, current and next calendar month. Each
calendar/month is capped at 500 entries and the number of calendars is capped at 20. Recurrence expansion failures, request failures and collection caps mark the
results partial. The UI distinguishes no matching events, partial results, and
outside coverage; browsing outside the range never implies free time. Thunderbird
client cache collection is not proof of server sync. Undated tasks remain separate.
The existing bridge supports date ranges, so its source requires no modification.

The short writeup is derived from the existing preference-filtered synthesized
brief; the complete edition and citations remain accessible. Refresh reloads the
published edition and local health, without collecting accounts or regenerating.
A failed refresh retains the displayed edition and warns that it is retained.

GitHub adds own open PRs, requested reviews, assigned issues, recent activity and
accessible user projects to unread notifications. Each query is bounded; unavailable
project permissions, bounded activity and organization-project gaps are explicit.
Photo cleanup pause and local service scope/failed states remain visible.

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

Official documentation consulted 2026-11-18:

- [Personal API and token exchange](https://developer.garmin.com/gc-developer-program/personal/personal-api/)
- [Official OpenAPI schemas](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/)

Requests use the documented Personal API host. Token POST uses `ApiKey` auth;
subsequent requests use the returned bearer token. The token endpoint returns
**plain text**, and rejects `Accept: application/json` with HTTP 406; do not
negotiate or parse JSON for token exchange. Data endpoints return JSON.
Live token exchange and the original four data endpoints were verified on 2026-11-11. The expanded six data requests were verified on 2026-11-18; current-day readings were absent while historical records were available.
The reviewed public OpenAPI v1.0.0 supplies these paths and fields:

| Resource      | Request                                                                                                                       | Published fields                                                                           |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Sleep         | `/sleep-service/sleep/dailySleep?date=YYYY-MM-DD`                                                                             | calendarDate, sleepTimeSeconds, sleepScores.overall.value, sleepEndTimestampGMT            |
| Daily summary | `/usersummary-service/usersummary/daily?calendarDate=YYYY-MM-DD`                                                              | calendarDate, totalSteps, restingHeartRate, bodyBatteryMostRecentValue, wellnessEndTimeGmt |
| HRV           | `/hrv-service/hrv/YYYY-MM-DD`                                                                                                 | hrvSummary.calendarDate, hrvSummary.lastNightAvg, endTimestampGMT                          |
| Activities    | `/activitylist-service/activities/search/activities?start=0&limit=100&sortOrder=desc&startDate=YYYY-MM-DD&endDate=YYYY-MM-DD` | activityName, startTimeGMT, activityType.typeKey, duration, distance, averageHR            |
| Sleep history | `/sleep-service/sleep/dailySleepSummariesByDate?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD`                                      | 14 days of projected sleep date, duration, score, observation                              |
| Steps history | `/usersummary-service/stats/steps/daily/START/END`                                                                            | 14 days of calendarDate, totalSteps, totalDistance                                         |

Daily summary also projects distance, active energy, average stress, moderate and
vigorous intensity minutes, and floors climbed. Activity history spans 31 days,
with a maximum of 100 entries; reaching that cap is partial. Sleep/steps history
spans 14 days. Requests carry source/requested time and range, collection time,
and observed date range where available. Missing values remain missing, including
when today has no reading but earlier dates do. No advice is generated.

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
status/times, the photo projection and local unit status. Raw snapshots, mail, full partner-calendar objects, prompts, logs, private preferences and credentials are never served. Calendar projection contains only safe event titles, dates, categories, ownership labels and opaque dashboard aliases; raw UUIDs, descriptions, attendees and arbitrary URLs are omitted. Garmin and GitHub also pass explicit publication allowlists. The brief itself is private personal content: do not publish screenshots
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
node --test scripts/check-morning-dashboard.cjs scripts/check-agent-garmin.cjs scripts/check-dashboard-sources.cjs
# Isolated local source UI check using an existing Playwright installation and Chromium:
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

Schedule evidence on 2026-11-18: actual systemd collector `OnCalendar=*-*-*
07:00:00 Europe/Berlin`, `Persistent=true`, `AccuracySec=1s`; actual enabled T3
fixed-time delivery 07:10 Europe/Berlin (next run 2026-11-19T06:10:00.000Z).
This change modifies neither schedule. Historical verification above refers to
the earlier deployed dashboard; the calendar implementation is verified locally
with isolated headless Chromium and synthetic fixtures. Parent delivery owns
private backup, deployment and deployed verification after independent review.
