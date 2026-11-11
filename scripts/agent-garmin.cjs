// Official Personal API only. Neither keys nor short-lived tokens are persisted in snapshots.
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
const base = "https://personal.connectapi.garmin.com";
const now = () => new Date().toISOString();
const number = (value) =>
  typeof value === "number" && Number.isFinite(value) && value >= 0
    ? value
    : null;
async function collectGarmin({ fetchImpl = fetch, key, date } = {}) {
  date ||= new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
  }).format(new Date());
  if (key === undefined) {
    key = process.env.GARMIN_API_KEY;
    if (!key) {
      try {
        const file = path.join(
          os.homedir(),
          ".config/agent-life/garmin-api-key",
        );
        const stat = await fs.stat(file);
        if (stat.mode & 0o077 || stat.uid !== process.getuid())
          throw new Error("private key permissions");
        key = (await fs.readFile(file, "utf8")).trim();
      } catch (error) {
        if (error.code !== "ENOENT")
          return {
            state: "unavailable",
            attemptedAt: now(),
            repair:
              "Check the owner and mode 0600 of the private Garmin key file.",
          };
      }
    }
  }
  if (!key?.trim())
    return {
      state: "not_connected",
      attemptedAt: now(),
      repair: "Configure a Garmin Personal API key on homelab-dev.",
    };
  async function request(endpoint, authorization, method = "GET", format = "json") {
    const response = await fetchImpl(base + endpoint, {
      method,
      headers: {
        Authorization: authorization,
        ...(format === "json" ? { Accept: "application/json" } : {}),
      },
      signal: AbortSignal.timeout(20000),
      redirect: "error",
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (response.status === 204) return null;
    return format === "text" ? response.text() : response.json();
  }
  let token;
  try {
    const result = await request(
      "/personalapitoken-service/personal-api/personal-api-key/token",
      `ApiKey ${key.trim()}`,
      "POST",
      "text",
    );
    token = typeof result === "string" ? result.trim() : "";
    if (!token || /\s/.test(token))
      throw new Error("Unsupported token response");
  } catch {
    return {
      state: "unavailable",
      attemptedAt: now(),
      repair:
        "Garmin token exchange failed. Check key expiry and official API availability.",
    };
  }
  const endpoints = {
    sleep: `/sleep-service/sleep/dailySleep?date=${date}`,
    daily: `/usersummary-service/usersummary/daily?calendarDate=${date}`,
    hrv: `/hrv-service/hrv/${date}`,
    activities:
      "/activitylist-service/activities/search/activities?start=0&limit=5&sortOrder=desc",
  };
  const results = {};
  await Promise.all(
    Object.entries(endpoints).map(async ([name, endpoint]) => {
      try {
        const raw = await request(endpoint, `Bearer ${token}`);
        let data;
        if (name === "sleep")
          data = {
            date: raw?.calendarDate ?? null,
            seconds: number(raw?.sleepTimeSeconds),
            score: number(raw?.sleepScores?.overall?.value),
            observedAt: raw?.sleepEndTimestampGMT ?? null,
          };
        if (name === "daily")
          data = {
            date: raw?.calendarDate ?? null,
            steps: number(raw?.totalSteps),
            restingHeartRate: number(raw?.restingHeartRate),
            bodyBattery: number(raw?.bodyBatteryMostRecentValue),
            observedAt: raw?.wellnessEndTimeGmt ?? null,
          };
        if (name === "hrv")
          data = {
            date: raw?.hrvSummary?.calendarDate ?? null,
            overnightAverage: number(raw?.hrvSummary?.lastNightAvg),
            observedAt: raw?.endTimestampGMT ?? null,
          };
        if (name === "activities") {
          if (raw !== null && !Array.isArray(raw))
            throw new Error("Unsupported activity response");
          data = (raw || [])
            .slice(0, 5)
            .map((a) => ({
              name:
                typeof a.activityName === "string"
                  ? a.activityName.slice(0, 150)
                  : "Activity",
              startTimeGMT: a.startTimeGMT ?? null,
              durationSeconds: number(a.duration),
              distanceMeters: number(a.distance),
            }));
        }
        const empty =
          raw === null ||
          (Array.isArray(data)
            ? !data.length
            : Object.entries(data)
                .filter(([k]) => !["date", "observedAt"].includes(k))
                .every(([, v]) => v === null));
        results[name] = {
          state: empty ? "no_data" : "ok",
          collectedAt: now(),
          data,
        };
      } catch {
        results[name] = { state: "unavailable", attemptedAt: now() };
      }
    }),
  );
  return {
    state: Object.values(results).every((r) => r.state === "unavailable")
      ? "unavailable"
      : Object.values(results).some((r) => r.state !== "ok")
        ? "partial"
        : "ok",
    collectedAt: now(),
    date,
    data: results,
  };
}
module.exports = { collectGarmin };
