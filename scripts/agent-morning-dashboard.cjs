#!/usr/bin/env node
// Publish an explicit projection, never a filesystem browser or raw collector API.
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
const http = require("node:http");
const { photosStatus, localHealth } = require("./agent-life-status.cjs");
const {
  projectCalendar,
  projectGithub,
} = require("./agent-dashboard-sources.cjs");
const state =
  process.env.MORNING_STATE_DIR ||
  path.join(os.homedir(), ".local/state/agent-life");
const assets = path.join(__dirname, "../web/morning");
const iso = () => new Date().toISOString();
function sanitizeReport(text) {
  return text
    .replace(/https?:\/\/[^\s<>"')\]]+/gi, (raw) => {
      try {
        const url = new URL(raw);
        if (/auth|token|login|verify|unsubscribe|confirm/i.test(url.pathname))
          return "[private link omitted]";
        if (url.protocol !== "https:") return "[private link omitted]";
        if (
          url.hostname === "github.com" &&
          /^(?:\/[\w.-]+\/[\w.-]+\/(?:pull|issues|projects)\/\d+|\/(?:users|orgs)\/[\w.-]+\/projects\/\d+|\/[\w.-]+\/[\w.-]+\/commit\/[0-9a-f]{40})$/.test(
            url.pathname,
          )
        )
          return url.origin + url.pathname;
        if (
          url.hostname === "moodle.tu-dortmund.de" &&
          [
            "/course/view.php",
            "/mod/assign/view.php",
            "/mod/forum/discuss.php",
            "/mod/forum/view.php",
            "/mod/choice/view.php",
          ].includes(url.pathname)
        ) {
          const query = new URLSearchParams();
          for (const name of ["id", "d"])
            if (/^\d+$/.test(url.searchParams.get(name) || ""))
              query.set(name, url.searchParams.get(name));
          return url.origin + url.pathname + (query.size ? "?" + query : "");
        }
        // Unknown hosts may carry signed credentials in path segments as well as queries.
        return "[private link omitted]";
      } catch {
        return "[link omitted]";
      }
    })
    .replace(
      /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi,
      "[private identifier omitted]",
    )
    .replace(/\b(?:Bearer|ApiKey)\s+\S+/gi, "[credential omitted]");
}
// Re-project at publication: snapshots are private inputs, not trusted public schemas.
function projectGarmin(input) {
  const stateOf = (value) =>
    ["ok", "partial", "no_data", "unavailable", "not_connected"].includes(value)
      ? value
      : "unavailable";
  const dateOf = (value) => {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value))
      return null;
    const parsed = new Date(value);
    return Number.isFinite(parsed.getTime()) &&
      parsed.toISOString().slice(0, 10) === value
      ? value
      : null;
  };
  const timeOf = (value) => {
    if (
      typeof value !== "string" ||
      !/^\d{4}-\d{2}-\d{2}T[\d:.]+(?:Z|[+-]\d{2}:\d{2})$/.test(value)
    )
      return null;
    const parsed = new Date(value);
    return Number.isFinite(parsed.getTime()) ? parsed.toISOString() : null;
  };
  const rangeOf = (value) => {
    const start = dateOf(value?.start),
      end = dateOf(value?.end);
    return start && end && start <= end ? { start, end } : null;
  };
  const numberOf = (value) =>
    typeof value === "number" && Number.isFinite(value) && value >= 0
      ? value
      : null;
  const readings = (value, fields) =>
    Object.fromEntries([
      ["date", dateOf(value?.date)],
      ["observedAt", timeOf(value?.observedAt)],
      ...fields.map((field) => [field, numberOf(value?.[field])]),
    ]);
  const fields = {
    sleep: ["seconds", "score"],
    daily: [
      "steps",
      "restingHeartRate",
      "bodyBattery",
      "distanceMeters",
      "activeKilocalories",
      "stressAverage",
      "moderateIntensityMinutes",
      "vigorousIntensityMinutes",
      "floorsAscended",
    ],
    hrv: ["overnightAverage"],
  };
  const data = {};
  for (const name of [
    "sleep",
    "daily",
    "hrv",
    "activities",
    "sleepHistory",
    "stepsHistory",
  ]) {
    const endpoint = input?.data?.[name];
    if (!endpoint || typeof endpoint !== "object") continue;
    let projected;
    if (name === "activities")
      projected = Array.isArray(endpoint.data)
        ? endpoint.data.slice(0, 100).map((activity) => ({
            name:
              typeof activity?.name === "string"
                ? sanitizeReport(activity.name).slice(0, 150)
                : "Activity",
            date: dateOf(activity?.date),
            startTimeGMT: timeOf(activity?.startTimeGMT),
            type:
              typeof activity?.type === "string" &&
              /^[a-z_]{1,60}$/.test(activity.type)
                ? activity.type
                : null,
            durationSeconds: numberOf(activity?.durationSeconds),
            distanceMeters: numberOf(activity?.distanceMeters),
            averageHeartRate: numberOf(activity?.averageHeartRate),
          }))
        : [];
    else if (name.endsWith("History"))
      projected = Array.isArray(endpoint.data)
        ? endpoint.data
            .slice(0, 14)
            .map((value) =>
              readings(
                value,
                name === "sleepHistory"
                  ? fields.sleep
                  : ["steps", "distanceMeters"],
              ),
            )
        : [];
    else projected = readings(endpoint.data, fields[name]);
    data[name] = {
      state: stateOf(endpoint.state),
      source: "Garmin Personal API",
      requestedAt: timeOf(endpoint.requestedAt),
      collectedAt: timeOf(endpoint.collectedAt),
      attemptedAt: timeOf(endpoint.attemptedAt),
      requestedRange: rangeOf(endpoint.requestedRange),
      observedRange: rangeOf(endpoint.observedRange),
      truncated: endpoint.truncated === true,
      data: projected,
    };
  }
  return {
    state: stateOf(input?.state || "not_connected"),
    date: dateOf(input?.date),
    collectedAt: timeOf(input?.collectedAt),
    attemptedAt: timeOf(input?.attemptedAt),
    activityRange: rangeOf(input?.activityRange),
    historyRange: rangeOf(input?.historyRange),
    data,
  };
}
async function publish() {
  const reportPath = path.join(state, "latest-brief.md");
  const [report, stat, snapshot] = await Promise.all([
    fs.readFile(reportPath, "utf8"),
    fs.stat(reportPath),
    fs.readFile(path.join(state, "snapshot.json"), "utf8").then(JSON.parse),
  ]);
  if (!report.trim() || report.length > 150000)
    throw new Error("Brief is empty or too large");
  const sourceNames = [
    "mail",
    "universityMail",
    "localCalendar",
    "reviewedAttachments",
    "github",
    "garmin",
    "photoMigration",
    "localHealth",
  ];
  const sourceStates = [
    "ok",
    "partial",
    "unavailable",
    "not_connected",
    "no_data",
  ];
  const timestamp = (value) =>
    typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T/.test(value) &&
    Number.isFinite(Date.parse(value))
      ? new Date(value).toISOString()
      : null;
  const sources = Object.entries(snapshot.sources || {})
    .filter(([name]) => sourceNames.includes(name))
    .map(([name, source]) => ({
      name,
      state: sourceStates.includes(source?.state)
        ? source.state
        : "unavailable",
      collectedAt: timestamp(source?.collectedAt),
      attemptedAt: timestamp(source?.attemptedAt),
    }));
  let preferences = "";
  try {
    preferences = await fs.readFile(
      path.join(state, "brief-preferences.txt"),
      "utf8",
    );
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  const data = {
    publishedAt: iso(),
    report: sanitizeReport(report),
    reportUpdatedAt: stat.mtime.toISOString(),
    sourceCollectedAt: timestamp(snapshot.collectedAt),
    date:
      typeof snapshot.date === "string" &&
      /^\d{4}-\d{2}-\d{2}$/.test(snapshot.date) &&
      Number.isFinite(Date.parse(snapshot.date))
        ? snapshot.date
        : null,
    timeZone: "Europe/Berlin",
    sources,
    garmin: projectGarmin(snapshot.sources?.garmin),
    photos: snapshot.sources?.photoMigration?.data
      ? {
          updatedAt: timestamp(snapshot.sources.photoMigration.data.updatedAt),
          verifiedAt: timestamp(
            snapshot.sources.photoMigration.data.verifiedAt,
          ),
          backupVerified:
            snapshot.sources.photoMigration.data.backupVerified === true,
          cleanupPaused:
            snapshot.sources.photoMigration.data.cleanupPaused === true,
          cloudMediaChanged:
            snapshot.sources.photoMigration.data.cloudMediaChanged === true,
          subscriptionChanged:
            snapshot.sources.photoMigration.data.subscriptionChanged === true,
        }
      : null,
    calendar: projectCalendar(snapshot.sources?.localCalendar, preferences),
    github: projectGithub(snapshot.sources?.github),
  };
  const target = path.join(state, "dashboard.json");
  await fs.writeFile(`${target}.pending`, JSON.stringify(data), {
    mode: 0o600,
  });
  await fs.rename(`${target}.pending`, target);
}
function createServer() {
  return http.createServer(async (req, res) => {
    const headers = {
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "Content-Security-Policy":
        "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
      "X-Frame-Options": "DENY",
    };
    if (!["GET", "HEAD"].includes(req.method)) {
      res.writeHead(405, headers);
      return res.end();
    }
    // Tailscale Serve removes /morning; support both for direct local verification.
    const route =
      req.url.split("?")[0].replace(/^\/morning(?=\/|$)/, "") || "/";
    const files = {
      "/": ["index.html", "text/html; charset=utf-8"],
      "/index.html": ["index.html", "text/html; charset=utf-8"],
      "/app.js": ["app.js", "text/javascript; charset=utf-8"],
      "/style.css": ["style.css", "text/css; charset=utf-8"],
    };
    try {
      let body, type;
      if (route === "/data") {
        let published;
        try {
          published = JSON.parse(
            await fs.readFile(path.join(state, "dashboard.json"), "utf8"),
          );
        } catch {
          published = {
            report: null,
            error:
              "No published brief available. Check the morning brief service on homelab-dev.",
          };
        }
        const health = await localHealth();
        body = JSON.stringify({ ...published, health, servedAt: iso() });
        type = "application/json; charset=utf-8";
      } else if (files[route]) {
        const [file, mime] = files[route];
        body = await fs.readFile(path.join(assets, file));
        type = mime;
      } else {
        res.writeHead(404, headers);
        return res.end("Not found");
      }
      res.writeHead(200, { ...headers, "Content-Type": type });
      res.end(req.method === "HEAD" ? undefined : body);
    } catch {
      res.writeHead(503, headers);
      res.end("Dashboard temporarily unavailable");
    }
  });
}
module.exports = { publish, createServer, sanitizeReport, projectGarmin };
if (require.main === module) {
  process.umask(0o077);
  if (process.argv[2] === "publish")
    publish().catch(() => {
      console.error(
        "Dashboard publication failed; previous published brief retained.",
      );
      process.exitCode = 1;
    });
  else
    createServer().listen(
      Number(process.env.MORNING_PORT || 8787),
      "127.0.0.1",
      () => console.log("Morning dashboard listening on loopback."),
    );
}
