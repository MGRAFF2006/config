// Bounded source collection and explicit projections for the private dashboard.
const iso = () => new Date().toISOString();
const safeState = (value) =>
  ["ok", "partial", "unavailable", "not_connected", "no_data"].includes(value)
    ? value
    : "unavailable";
const day = (value) =>
  typeof value === "string" &&
  /^\d{4}-\d{2}-\d{2}/.test(value) &&
  Number.isFinite(Date.parse(value))
    ? value.slice(0, 10)
    : null;
const instant = (value) =>
  typeof value === "string" && Number.isFinite(Date.parse(value))
    ? new Date(value).toISOString()
    : null;
const uuid =
  /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;
function text(value, limit = 240) {
  if (typeof value !== "string") return "";
  return value
    .replace(/https?:\/\/\S+/gi, "[link omitted]")
    .replace(uuid, "[private identifier]")
    .replace(/\b(?:Bearer|ApiKey)\s+\S+/gi, "[credential omitted]")
    .replace(/[\u0000-\u001f]/g, " ")
    .slice(0, limit);
}
function ownershipMap(preferences) {
  const ids = (part) =>
    new Set(((part || "").match(uuid) || []).map((id) => id.toLowerCase()));
  const own = ids(
    preferences.match(/Mathis owns:([\s\S]*?)(?:His girlfriend owns:|$)/)?.[1],
  );
  const partner = ids(
    preferences.match(
      /His girlfriend owns:([\s\S]*?)(?:Emma und Mathis|Ownership of other calendars|$)/,
    )?.[1],
  );
  const shared = ids(
    preferences.match(/Emma und Mathis\s*\(([^)]+)\)\s*is shared context/)?.[1],
  );
  return (id) => {
    const value = typeof id === "string" ? id.toLowerCase() : "";
    return own.has(value)
      ? "own"
      : partner.has(value)
        ? "partner"
        : shared.has(value)
          ? "shared"
          : "unconfirmed";
  };
}
function calendarRange(now = new Date()) {
  const today = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
  }).format(now);
  const [year, month] = today.split("-").map(Number);
  return {
    start: new Date(Date.UTC(year, month - 2, 1)).toISOString().slice(0, 10),
    end: new Date(Date.UTC(year, month + 1, 1)).toISOString().slice(0, 10),
  };
}
function berlinMidnight(date) {
  const offset = new Intl.DateTimeFormat("en", {
    timeZone: "Europe/Berlin",
    timeZoneName: "shortOffset",
  })
    .formatToParts(new Date(date + "T12:00:00Z"))
    .find((p) => p.type === "timeZoneName").value;
  const match = offset.match(/GMT([+-])(\d+)(?::(\d+))?/);
  const minutes = match
    ? (Number(match[2]) * 60 + Number(match[3] || 0)) *
      (match[1] === "+" ? 1 : -1)
    : 0;
  return new Date(
    Date.parse(date + "T00:00:00Z") - minutes * 60000,
  ).toISOString();
}
async function collectCalendar(call, now = new Date()) {
  const range = calendarRange(now),
    requestedAt = iso();
  const calendars = await call("listCalendars");
  if (!Array.isArray(calendars)) throw Error("Calendar listing unavailable");
  const active = calendars.filter(
    (c) => !c.disabled && !c.name?.includes("⚠"),
  );
  if (!active.length) throw Error("No enabled calendars available");
  const events = [],
    tasks = [],
    failures = [],
    seen = new Set();
  let eventsTruncated = false,
    tasksTruncated = false;
  // Query calendars separately so one busy calendar cannot consume another's cap.
  // Calendar-month buckets also keep recurring expansion safely bounded.
  for (const c of active.slice(0, 20)) {
    if (c.supportsEvents !== false) {
      for (
        let cursor = new Date(range.start + "T00:00:00Z");
        cursor.toISOString().slice(0, 10) < range.end;

      ) {
        const startDate = berlinMidnight(cursor.toISOString().slice(0, 10));
        cursor = new Date(
          Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 1),
        );
        try {
          const result = await call("listEvents", {
            calendarId: c.id,
            startDate,
            endDate: berlinMidnight(cursor.toISOString().slice(0, 10)),
            maxResults: 500,
          });
          if (!Array.isArray(result)) throw Error("Unavailable calendar");
          if (result.length >= 500) eventsTruncated = true;
          for (const event of result) {
            const key = JSON.stringify([
              c.id,
              event.id,
              event.recurrenceId,
              event.startDate,
            ]);
            if (!seen.has(key)) {
              seen.add(key);
              events.push({ ...event, calendarId: c.id, calendarName: c.name });
            }
          }
        } catch {
          failures.push({ calendarId: c.id, kind: "events" });
        }
      }
    }
    if (c.supportsTasks) {
      try {
        const result = await call("listTasks", {
          calendarId: c.id,
          completed: false,
          dueBefore: berlinMidnight(range.end),
          maxResults: 500,
        });
        if (!Array.isArray(result)) throw Error("Unavailable tasks");
        if (result.length >= 500) tasksTruncated = true;
        tasks.push(
          ...result.map((task) => ({
            ...task,
            calendarId: c.id,
            calendarName: c.name,
          })),
        );
      } catch {
        failures.push({ calendarId: c.id, kind: "tasks" });
      }
    }
  }
  return {
    requestedAt,
    range,
    calendars,
    events,
    tasks,
    failures,
    limits: {
      eventsTruncated,
      tasksTruncated,
      calendarLimit: active.length > 20,
      recurrenceNotExpanded: events.some((e) => e.recurrenceNotExpanded),
    },
    coverage:
      "Thunderbird client cache; per-calendar server sync times are unavailable.",
    taskCoverage:
      "Compatibility-warning calendars excluded. Modern Apple Reminders unavailable; task backends may silently omit failed collections.",
  };
}
function dismissed(title, preferences) {
  // Only explicit, narrowly identified dismissals; an acknowledged date is not completion.
  return (
    (/mobility survey|mobilitätsbefrag/i.test(title) &&
      /completed the TU Dortmund mobility survey/.test(preferences)) ||
    (/Physik\s*(?:I\b|1\b)/i.test(title) &&
      /Physik I Moodle course for access only/.test(preferences)) ||
    (/HöMa I\b.*(?:nach|makeup|Blatt 3)/i.test(title) &&
      /does not need a makeup test/.test(preferences)) ||
    (/Zukunftsdialog/.test(title) &&
      /declined the Zukunftsdialog invitation for 2026-11-10/.test(
        preferences,
      ) &&
      /2026-11-10/.test(title))
  );
}
function projectCalendar(source, preferences = "") {
  const data = source?.data || {};
  const range =
    data.range && day(data.range.start) && day(data.range.end)
      ? { start: day(data.range.start), end: day(data.range.end) }
      : null;
  const owner = ownershipMap(preferences),
    limitations = [];
  const flags = data.limits || {};
  if (flags.eventsTruncated || flags.tasksTruncated || flags.calendarLimit)
    limitations.push(
      "A collection cap was reached; some items may be missing.",
    );
  if (flags.recurrenceNotExpanded)
    limitations.push(
      "Some recurring events could not be expanded and are omitted.",
    );
  if (data.failures?.length)
    limitations.push(
      "Some calendar requests failed; missing items do not establish free time.",
    );
  limitations.push(
    "Client cache only; upstream server sync time is unavailable.",
    "Modern Apple Reminders unavailable; task backend completeness cannot be verified.",
  );
  const partial = Boolean(
    data.failures?.length || Object.values(flags).some(Boolean),
  );
  const events = [],
    undatedTasks = [];
  function add(item, kind) {
    if (
      !item ||
      typeof item !== "object" ||
      item.completed ||
      item.status === "cancelled" ||
      item.myParticipationStatus === "DECLINED" ||
      item.recurrenceNotExpanded ||
      dismissed(item.title || "", preferences)
    )
      return;
    const ownership = owner(item.calendarId);
    const category =
      ownership !== "own"
        ? "shared"
        : /studium/i.test(item.calendarName || "")
          ? "study"
          : /arbeit|judo|JCH/i.test(item.calendarName || "")
            ? "club"
            : "own";
    const startRaw = kind === "deadline" ? item.dueDate : item.startDate;
    const allDay =
      kind === "deadline"
        ? Boolean(startRaw && /^\d{4}-\d{2}-\d{2}$/.test(startRaw))
        : Boolean(item.allDay);
    const start = allDay ? day(startRaw) : instant(startRaw);
    // Thunderbird's all-day end is inclusive; dashboard end is exclusive.
    let end = allDay ? day(item.endDate || startRaw) : instant(item.endDate);
    if (allDay && end)
      end = new Date(Date.parse(end + "T00:00:00Z") + 86400000)
        .toISOString()
        .slice(0, 10);
    const title =
      text(item.title) ||
      (kind === "deadline" ? "Untitled deadline" : "Untitled event");
    const result = {
      id: `calendar-item-${events.length + undatedTasks.length + 1}`,
      title,
      start,
      end,
      allDay,
      category,
      ownership,
      calendar: text(item.calendarName, 80),
      kind,
      source: "Thunderbird calendar",
      observedAt: null,
    };
    if (
      /Trainer Fortbildung JCH/i.test(title) &&
      day(start) === "2026-11-14" &&
      /November 14 as unconfirmed/.test(preferences)
    )
      result.confirmation =
        "Date unconfirmed; a move was reported but upstream sync is unknown.";
    if (
      /HöMa III/i.test(title) &&
      /HöMa III sheets are optional/.test(preferences)
    )
      result.confirmation = "Optional study opportunity.";
    if (!start) {
      if (kind === "deadline") undatedTasks.push(result);
      return;
    }
    if (!range || day(start) >= range.end || day(end || start) < range.start)
      return;
    events.push(result);
  }
  for (const item of (data.events || []).slice(0, 30000)) add(item, "event");
  for (const item of (data.tasks || []).slice(0, 10000)) add(item, "deadline");
  return {
    state:
      source?.state === "ok"
        ? partial
          ? "partial"
          : "ok"
        : safeState(source?.state),
    collectedAt: instant(source?.collectedAt),
    attemptedAt: instant(source?.attemptedAt),
    requestedAt: instant(data.requestedAt),
    range:
      range && day(range.start) && day(range.end)
        ? { start: day(range.start), end: day(range.end) }
        : null,
    cache: "Thunderbird client cache; server sync time unavailable",
    partial,
    limitations,
    events,
    undatedTasks,
  };
}
function githubURL(raw) {
  try {
    const u = new URL(raw);
    return u.protocol === "https:" &&
      u.hostname === "github.com" &&
      /^(?:\/[\w.-]+\/[\w.-]+\/(?:pull|issues|projects)\/\d+|\/(?:users|orgs)\/[\w.-]+\/projects\/\d+|\/[\w.-]+\/[\w.-]+\/commit\/[0-9a-f]{40})$/.test(
        u.pathname,
      )
      ? u.origin + u.pathname
      : null;
  } catch {
    return null;
  }
}
async function collectGithub(run) {
  const requestedAt = iso();
  const api = async (args) =>
    JSON.parse(
      (
        await run("gh", ["api", ...args], {
          timeout: 30000,
          maxBuffer: 2 * 1024 * 1024,
        })
      ).stdout,
    );
  const user = await api(["user"]);
  if (!/^[\w-]+$/.test(user.login)) throw Error("Invalid login");
  const results = {},
    failures = [];
  const queries = {
    notifications: ["notifications?per_page=50"],
    ownPRs: [
      "-X",
      "GET",
      "search/issues",
      "-f",
      `q=is:pr is:open author:${user.login}`,
      "-f",
      "per_page=30",
    ],
    reviews: [
      "-X",
      "GET",
      "search/issues",
      "-f",
      `q=is:pr is:open review-requested:${user.login}`,
      "-f",
      "per_page=30",
    ],
    issues: [
      "-X",
      "GET",
      "search/issues",
      "-f",
      `q=is:issue is:open assignee:${user.login}`,
      "-f",
      "per_page=30",
    ],
    activity: [`users/${user.login}/events?per_page=30`],
    projects: [
      "graphql",
      "-f",
      "query={viewer{projectsV2(first:10){nodes{title url closed updatedAt} pageInfo{hasNextPage}}}}",
    ],
  };
  await Promise.all(
    Object.entries(queries).map(async ([name, args]) => {
      try {
        results[name] = await api(args);
      } catch {
        failures.push(name);
      }
    }),
  );
  return {
    requestedAt,
    results,
    failures,
    scope:
      "Up to 50 unread notifications, 30 own open PRs, 30 requested reviews, 30 assigned issues, 30 recent activity events and 10 user projects. Organization projects are not enumerated.",
  };
}
function projectGithub(source) {
  const data = source?.data || {},
    results = data.results || {},
    items = [],
    seen = new Set(),
    limitations = [];
  const add = (item, kind) => {
    const url = githubURL(item.html_url || item.url);
    if (!url || seen.has(url)) return;
    seen.add(url);
    items.push({
      title: text(item.title) || kind,
      url,
      repository: text(
        item.repository_url?.split("/repos/")[1] ||
          new URL(url).pathname.split("/").slice(1, 3).join("/"),
        100,
      ),
      kind,
      updatedAt: instant(item.updated_at || item.updatedAt),
    });
  };
  for (const [key, kind] of [
    ["reviews", "Review requested"],
    ["ownPRs", "Your open PR"],
    ["issues", "Assigned issue"],
  ]) {
    const result = results[key];
    for (const item of result?.items || []) add(item, kind);
    if (result?.incomplete_results || result?.total_count > 30)
      limitations.push(`${kind}: additional results not collected.`);
  }
  for (const item of results.projects?.data?.viewer?.projectsV2?.nodes || [])
    if (!item.closed) add(item, "Project");
  // Activity payloads contain commit text and private identities: project only safe PR/issue references.
  for (const event of results.activity || []) {
    const item = event.payload?.pull_request || event.payload?.issue;
    if (item)
      add(
        { ...item, updated_at: item.updated_at || event.created_at },
        "Recent activity",
      );
    if (
      event.type === "PushEvent" &&
      /^[\w.-]+\/[\w.-]+$/.test(event.repo?.name || "") &&
      /^[0-9a-f]{40}$/.test(event.payload?.head || "")
    )
      add(
        {
          title: `Pushed changes to ${event.repo.name}`,
          html_url: `https://github.com/${event.repo.name}/commit/${event.payload.head}`,
          updated_at: event.created_at,
        },
        "Recent push",
      );
  }
  for (const n of results.notifications || []) {
    const match = n.subject?.url?.match(
      /^https:\/\/api.github.com\/repos\/([\w.-]+\/[\w.-]+)\/(pulls|issues)\/(\d+)$/,
    );
    if (match)
      add(
        {
          title: n.subject.title,
          html_url: `https://github.com/${match[1]}/${match[2] === "pulls" ? "pull" : "issues"}/${match[3]}`,
          updated_at: n.updated_at,
        },
        "Notification",
      );
  }
  if ((results.activity || []).length >= 30)
    limitations.push("Recent activity reached the 30-event cap.");
  if ((results.notifications || []).length >= 50)
    limitations.push("Notifications reached the 50-item cap.");
  if (results.projects?.data?.viewer?.projectsV2?.pageInfo?.hasNextPage)
    limitations.push("Additional personal projects were not collected.");
  if (data.failures?.length)
    limitations.push(
      `Unavailable sources: ${data.failures.filter((x) => ["notifications", "ownPRs", "reviews", "issues", "activity", "projects"].includes(x)).join(", ")}.`,
    );
  limitations.push(text(data.scope || "GitHub coverage unavailable.", 400));
  limitations.push(
    "Activity API is a bounded recent history; organization project access and project item status are not covered.",
  );
  return {
    state:
      source?.state === "ok"
        ? data.failures?.length
          ? "partial"
          : "ok"
        : safeState(source?.state),
    collectedAt: instant(source?.collectedAt),
    requestedAt: instant(data.requestedAt),
    items,
    limitations,
  };
}
module.exports = {
  collectCalendar,
  projectCalendar,
  calendarRange,
  ownershipMap,
  collectGithub,
  projectGithub,
  text,
};
