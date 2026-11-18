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
function day(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
    return null;
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
    ? value
    : null;
}
function timestamp(value, gmt = false) {
  if (value == null) return null;
  if (typeof value === "string" && /^\d{13}$/.test(value))
    value = Number(value);
  if (
    typeof value === "string" &&
    gmt &&
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
  )
    value = value.replace(" ", "T") + "Z";
  if (
    typeof value !== "number" &&
    !(
      typeof value === "string" &&
      /^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(value)
    )
  )
    return null;
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? parsed.toISOString() : null;
}
const berlinDay = (value) =>
  new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Berlin" }).format(
    new Date(value),
  );
const offsetDay = (date, amount) =>
  new Date(Date.parse(date + "T12:00:00Z") + amount * 86400000)
    .toISOString()
    .slice(0, 10);
const safeName = (value) =>
  typeof value === "string"
    ? value
        .replace(/https?:\/\/\S+/gi, "[link withheld]")
        .replace(
          /[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}/gi,
          "[identifier withheld]",
        )
        .slice(0, 150)
    : "Activity";
const projectSleep = (raw) => ({
  date: day(raw?.calendarDate),
  seconds: number(raw?.sleepTimeSeconds),
  score: number(raw?.sleepScores?.overall?.value),
  observedAt: timestamp(raw?.sleepEndTimestampGMT),
});
async function collectGarmin({ fetchImpl = fetch, key, date } = {}) {
  date ||= new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
  }).format(new Date());
  if (!day(date)) throw new Error("Invalid Garmin requested date");
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
  async function request(
    endpoint,
    authorization,
    method = "GET",
    format = "json",
  ) {
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
  const activityRange = { start: offsetDay(date, -30), end: date };
  const historyRange = { start: offsetDay(date, -13), end: date };
  // Official Personal API Swagger verified 2026-11-18:
  // https://developer.garmin.com/gc-developer-program/personal/swagger-docs/
  // Bounded six data requests; no FIT files, GPS traces, account IDs or notes.
  const endpoints = {
    sleep: `/sleep-service/sleep/dailySleep?date=${date}`,
    daily: `/usersummary-service/usersummary/daily?calendarDate=${date}`,
    hrv: `/hrv-service/hrv/${date}`,
    activities: `/activitylist-service/activities/search/activities?start=0&limit=100&sortOrder=desc&startDate=${activityRange.start}&endDate=${activityRange.end}`,
    sleepHistory: `/sleep-service/sleep/dailySleepSummariesByDate?startDate=${historyRange.start}&endDate=${historyRange.end}`,
    stepsHistory: `/usersummary-service/stats/steps/daily/${historyRange.start}/${historyRange.end}`,
  };
  const results = {};
  await Promise.all(
    Object.entries(endpoints).map(async ([name, endpoint]) => {
      const requestedAt = now();
      const requestedRange =
        name === "activities"
          ? activityRange
          : name.endsWith("History")
            ? historyRange
            : { start: date, end: date };
      const metadata = {
        source: "Garmin Personal API",
        requestedAt,
        requestedRange,
      };
      try {
        const raw = await request(endpoint, `Bearer ${token}`);
        let data;
        if (name === "sleep") data = projectSleep(raw);
        if (name === "daily")
          data = {
            date: day(raw?.calendarDate),
            steps: number(raw?.totalSteps),
            restingHeartRate: number(raw?.restingHeartRate),
            bodyBattery: number(raw?.bodyBatteryMostRecentValue),
            observedAt: timestamp(raw?.wellnessEndTimeGmt, true),
            distanceMeters: number(raw?.totalDistanceMeters),
            activeKilocalories: number(raw?.activeKilocalories),
            stressAverage: number(raw?.averageStressLevel),
            moderateIntensityMinutes: number(raw?.moderateIntensityMinutes),
            vigorousIntensityMinutes: number(raw?.vigorousIntensityMinutes),
            floorsAscended: number(raw?.floorsAscended),
          };
        if (name === "hrv")
          data = {
            date: day(raw?.hrvSummary?.calendarDate),
            overnightAverage: number(raw?.hrvSummary?.lastNightAvg),
            observedAt: timestamp(raw?.endTimestampGMT),
          };
        if (name === "activities") {
          if (raw !== null && !Array.isArray(raw))
            throw new Error("Unsupported activity response");
          data = (raw || []).slice(0, 100).map((a) => {
            const startTimeGMT = timestamp(a.startTimeGMT, true);
            return {
              name: safeName(a.activityName),
              startTimeGMT,
              date: startTimeGMT ? berlinDay(startTimeGMT) : null,
              type:
                typeof a.activityType?.typeKey === "string" &&
                /^[a-z_]+$/.test(a.activityType.typeKey)
                  ? a.activityType.typeKey
                  : null,
              durationSeconds: number(a.duration),
              distanceMeters: number(a.distance),
              averageHeartRate: number(a.averageHR),
            };
          });
        }
        if (name.endsWith("History")) {
          if (raw !== null && !Array.isArray(raw))
            throw new Error("Unsupported history response");
          data = (raw || [])
            .slice(0, 14)
            .map((a) =>
              name === "sleepHistory"
                ? projectSleep(a)
                : {
                    date: day(a.calendarDate),
                    steps: number(a.totalSteps),
                    distanceMeters: number(a.totalDistance),
                  },
            )
            .filter(
              (a) =>
                a.date &&
                a.date >= historyRange.start &&
                a.date <= historyRange.end,
            )
            .sort((a, b) => a.date.localeCompare(b.date));
        }
        const empty =
          raw === null ||
          (Array.isArray(data)
            ? !data.length
            : Object.entries(data)
                .filter(([k]) => !["date", "observedAt"].includes(k))
                .every(([, v]) => v === null));
        results[name] = {
          ...metadata,
          state: empty
            ? "no_data"
            : name === "activities" && raw?.length >= 100
              ? "partial"
              : "ok",
          truncated: name === "activities" && raw?.length >= 100,
          observedRange: Array.isArray(data)
            ? (() => {
                const dates = data
                  .map((a) => a.date)
                  .filter(Boolean)
                  .sort();
                return dates.length
                  ? { start: dates[0], end: dates.at(-1) }
                  : null;
              })()
            : data.date
              ? { start: data.date, end: data.date }
              : null,
          collectedAt: now(),
          data,
        };
      } catch {
        results[name] = {
          ...metadata,
          state: "unavailable",
          attemptedAt: now(),
        };
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
    activityRange,
    historyRange,
    data: results,
  };
}
module.exports = { collectGarmin };
