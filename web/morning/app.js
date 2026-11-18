const $ = (id) => document.getElementById(id);
const format = (value) =>
  value && Number.isFinite(Date.parse(value))
    ? new Intl.DateTimeFormat("en-GB", {
        timeZone: "Europe/Berlin",
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(value))
    : "Time unavailable";
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
// Deliberately small Markdown subset: text always enters through textContent.
function inline(node, text) {
  const parts = text.split(
    /(\[[^\]]+\]\s*\((?:https?:\/\/|mid:)[^\s)]+\)|\*\*[^*]+\*\*|`[^`]+`)/g,
  );
  for (const part of parts) {
    const citation = part.match(/^\[([^\]]+)\]\s*\((mid:[^\s)]+)\)$/);
    if (citation) {
      const detail = element("details", undefined, "citation");
      detail.append(
        element("summary", citation[1]),
        element("code", citation[2]),
      );
      node.append(detail);
      continue;
    }
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (link) {
      const a = element("a", link[1]);
      a.href = link[2];
      a.rel = "noreferrer noopener";
      a.target = "_blank";
      node.append(a);
    } else if (part.startsWith("**") && part.endsWith("**"))
      node.append(element("strong", part.slice(2, -2)));
    else if (part.startsWith("`") && part.endsWith("`"))
      node.append(element("code", part.slice(1, -1)));
    else node.append(document.createTextNode(part));
  }
}
function report(text, root = $("report")) {
  root.replaceChildren();
  let list;
  for (const line of text.split("\n")) {
    if (!line.trim()) {
      list = null;
      continue;
    }
    const heading =
      line.match(/^(#{1,6})\s+(.+)/) || line.match(/^(\*\*)([^*]+)\*\*$/);
    const bullet = line.match(/^\s*(?:[-*]|\d+\.)\s+(.+)/);
    let node;
    if (heading) {
      list = null;
      node = element(heading[1].length === 1 ? "h2" : "h3");
      inline(node, heading[2]);
      root.append(node);
    } else if (bullet) {
      if (!list) {
        list = element("ul");
        root.append(list);
      }
      node = element("li");
      inline(node, bullet[1]);
      list.append(node);
    } else {
      list = null;
      node = element("p");
      inline(node, line);
      root.append(node);
    }
  }
}
// Derive modules only from the already published, preference-filtered report.
// Keep unknown sections in the overview and retain the full original below it.
function overview(text) {
  for (const id of ["priorities", "agenda", "followups", "report-limits"])
    $(id).replaceChildren();
  const sections = [];
  let current;
  for (const line of (text || "").split("\n")) {
    const heading =
      line.match(/^#{1,6}\s+(.+)$/) || line.match(/^\*\*([^*]+)\*\*$/);
    const coverage = line.match(
      /^\s*(Coverage:|\*\*Coverage:\*\*|\*\*Coverage\*\*:)\s*(.*)$/i,
    );
    if (heading || coverage) {
      current = {
        title: (heading || coverage)[1],
        lines: coverage ? [coverage[2]] : [],
      };
      sections.push(current);
    } else if (current) current.lines.push(line);
    else if (line.trim()) {
      current = { title: "From this edition", lines: [line] };
      sections.push(current);
    }
  }
  let hasPriorities = false;
  for (const section of sections) {
    if (!section.lines.some((line) => line.trim())) continue;
    const title = section.title.replace(/\*\*/g, "");
    const limits = /coverage|limitations|sources/i.test(title);
    const priority = /actions|priorities/i.test(title);
    const target = limits
      ? "report-limits"
      : priority
        ? "priorities"
        : /today|deadlines|next seven|upcoming|calendar/i.test(title)
          ? "agenda"
          : "followups";
    const node = element("section", undefined, limits ? "" : "report-module");
    node.append(element("h2", title));
    const content = element("div");
    const lines = section.lines;
    // Collapse extra bullets, never discard their text or contextual caveats.
    const bullets = lines
      .map((line, i) => (/^\s*(?:[-*]|\d+\.)\s+/.test(line) ? i : -1))
      .filter((i) => i >= 0);
    const visibleItems = priority ? 1 : 2;
    if (!limits && bullets.length > visibleItems) {
      const cut = bullets[visibleItems];
      report(lines.slice(0, cut).join("\n"), content);
      const rest = element("details", undefined, "more-items");
      rest.append(
        element(
          "summary",
          `More from this section (${bullets.length - visibleItems})`,
        ),
      );
      const body = element("div");
      report(lines.slice(cut).join("\n"), body);
      rest.append(body);
      content.append(rest);
    } else report(lines.join("\n"), content);
    node.append(content);
    $(target).append(node);
    if (priority) hasPriorities = true;
  }
  if (!hasPriorities)
    $("priorities").append(
      element("h2", "Priorities"),
      element(
        "p",
        text
          ? "No priorities section in this edition. See the report sections below."
          : "No brief published. The overview will appear after a successful morning edition.",
      ),
    );
}
const names = {
  mail: "Mail",
  universityMail: "University mail",
  localCalendar: "Calendars & tasks",
  reviewedAttachments: "Reviewed attachments",
  github: "GitHub notifications",
  garmin: "Garmin",
  photoMigration: "Photo migration checkpoint",
  localHealth: "Local services",
};
function wearable(g) {
  const root = $("garmin");
  root.replaceChildren();
  root.append(
    element(
      "span",
      {
        not_connected: "Not connected",
        unavailable: "Unavailable",
        partial: "Partial data",
        ok: "Connected",
      }[g?.state] || "Not collected",
      "status",
    ),
  );
  if (!g?.data) {
    root.append(
      element(
        "p",
        g?.state === "not_connected"
          ? "A Garmin Personal API key is needed. Your brief works without it."
          : "No readings available. Check the Garmin key and source health.",
      ),
    );
  }
  const sleep = g?.data?.sleep?.data,
    daily = g?.data?.daily?.data,
    hrv = g?.data?.hrv?.data;
  const values = [
    [
      "Sleep",
      sleep?.seconds == null
        ? null
        : `${Math.floor(sleep.seconds / 3600)}h ${Math.round((sleep.seconds % 3600) / 60)}m`,
      "",
    ],
    ["Sleep score", sleep?.score, "/100"],
    ["Resting HR", daily?.restingHeartRate, "bpm"],
    ["Overnight HRV", hrv?.overnightAverage, "ms"],
    ["Body Battery", daily?.bodyBattery, "/100"],
    ["Steps", daily?.steps, ""],
    [
      "Distance",
      daily?.distanceMeters == null
        ? null
        : (daily.distanceMeters / 1000).toFixed(1),
      "km",
    ],
    ["Active energy", daily?.activeKilocalories, "kcal"],
    ["Stress average", daily?.stressAverage, "/100"],
    ["Moderate activity", daily?.moderateIntensityMinutes, "min"],
    ["Vigorous activity", daily?.vigorousIntensityMinutes, "min"],
    ["Floors climbed", daily?.floorsAscended, ""],
  ];
  const dl = element("dl", undefined, "metrics");
  for (const [label, value, unit] of values) {
    const d = element("div");
    d.append(element("dt", label));
    const dd = element("dd", value == null ? "—" : String(value));
    if (value != null && unit) dd.append(element("small", ` ${unit}`));
    d.append(dd);
    dl.append(d);
  }
  root.append(
    dl,
    element(
      "p",
      `Requested day: ${g?.date || "unavailable"}. Missing readings are shown as —. Garmin data may lag device sync.`,
      "meta",
    ),
  );
  $("endpoint-times").replaceChildren(element("h3", "Garmin endpoint times"));
  for (const [name, result] of Object.entries(g?.data || {})) {
    $("endpoint-times").append(
      element(
        "p",
        `${name}: ${result.state}; source ${result.source || "Garmin"}; requested ${format(result.requestedAt)}${result.requestedRange ? ` (${result.requestedRange.start} to ${result.requestedRange.end})` : ""}${result.observedRange ? `; observed dates ${result.observedRange.start} to ${result.observedRange.end}` : ""}${result.truncated ? "; result capped" : ""}${result.data?.date ? `; day ${result.data.date}` : ""}; fetched ${format(result.collectedAt || result.attemptedAt)}${result.data?.observedAt ? `; observed ${result.data.observedAt}` : ""}`,
        "meta",
      ),
    );
  }
  const historyRoot = $("garmin-history");
  historyRoot.replaceChildren();
  const historyDetails = element("details");
  historyDetails.append(element("summary", "Sleep & steps history (14 days)"));
  const sleeps = g?.data?.sleepHistory,
    steps = g?.data?.stepsHistory;
  historyDetails.append(
    element(
      "p",
      `Sleep: ${sleeps?.state || "not collected"}; steps: ${steps?.state || "not collected"}. Requested ${g?.historyRange?.start || "unavailable"} to ${g?.historyRange?.end || "unavailable"}. Missing dates and readings are not zero.`,
      "meta",
    ),
  );
  const days = [
    ...new Set([
      ...(sleeps?.data || []).map((x) => x.date),
      ...(steps?.data || []).map((x) => x.date),
    ]),
  ]
    .filter(Boolean)
    .sort()
    .reverse();
  const table = element("table");
  const head = element("tr");
  for (const label of ["Date", "Sleep", "Score", "Steps"]) {
    const th = element("th", label);
    th.scope = "col";
    head.append(th);
  }
  const thead = element("thead");
  thead.append(head);
  table.append(thead);
  const tbody = element("tbody");
  for (const day of days) {
    const sleep = sleeps?.data?.find((x) => x.date === day),
      step = steps?.data?.find((x) => x.date === day),
      row = element("tr");
    for (const value of [
      day,
      sleep?.seconds == null ? "—" : `${(sleep.seconds / 3600).toFixed(1)} h`,
      sleep?.score ?? "—",
      step?.steps ?? "—",
    ])
      row.append(element("td", String(value)));
    tbody.append(row);
  }
  table.append(tbody);
  if (days.length) historyDetails.append(table);
  else historyDetails.append(element("p", "No historical readings returned."));
  historyRoot.append(historyDetails);
  const activities = g?.data?.activities?.data;
  const activityRoot = $("activities");
  activityRoot.replaceChildren();
  if (activities?.length) {
    const more = element("details", undefined, "more-items");
    more.append(
      element(
        "summary",
        `More activities (${Math.max(0, activities.length - 2)})`,
      ),
    );
    for (const [index, a] of activities.entries())
      (index < 2 ? activityRoot : more).append(
        element(
          "p",
          `${a.name} · ${format(a.startTimeGMT)}${a.durationSeconds == null ? "" : ` · ${Math.round(a.durationSeconds / 60)} min`}`,
        ),
      );
    if (activities.length > 2) activityRoot.append(more);
  } else
    activityRoot.append(
      element(
        "p",
        `No recent activities available (${g?.data?.activities?.state || g?.state || "not collected"}).`,
      ),
    );
}
async function load() {
  $("refresh").disabled = true;
  try {
    const response = await fetch("/morning/data", { cache: "no-store" });
    if (!response.ok) throw Error("fetch");
    const d = await response.json();
    $("date").textContent = new Intl.DateTimeFormat("en-GB", {
      timeZone: "Europe/Berlin",
      dateStyle: "full",
    }).format(new Date());
    $("freshness").textContent = `Brief prepared ${format(d.reportUpdatedAt)}`;
    const berlinDate = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Europe/Berlin",
    }).format(new Date());
    const stale =
      d.date !== berlinDate ||
      !Number.isFinite(Date.parse(d.sourceCollectedAt)) ||
      Date.now() - Date.parse(d.sourceCollectedAt) > 24 * 3600000 ||
      !Number.isFinite(Date.parse(d.reportUpdatedAt)) ||
      dayKey(d.reportUpdatedAt) !== berlinDate;
    const failed =
      d.sources
        ?.filter((s) => !["ok"].includes(s.state))
        .map((s) => names[s.name] || s.name) || [];
    $("notice").hidden = false;
    $("notice").textContent =
      (d.error ? `${d.error} ` : "") +
      (stale ? "This is an older brief. " : "") +
      `A morning edition, not a live agenda. Collected ${format(d.sourceCollectedAt)}; times are as reported when prepared. ${failed.length ? `Limited coverage: ${failed.join(", ")}.` : ""}`;
    overview(d.report);
    dailySummary(d.report);
    if (d.report) report(d.report);
    else
      $("report").replaceChildren(
        element("h2", "No brief published"),
        element(
          "p",
          "The last successful report will appear here after the morning service completes.",
        ),
      );
    wearable(d.garmin);
    dashboard = d;
    renderCalendar();
    github(d.github);
    $("photos").replaceChildren(
      element(
        "p",
        d.photos
          ? `${d.photos.backupVerified ? "Backup verified." : "Backup verification not confirmed."} ${d.photos.cleanupPaused ? "Cloud cleanup paused for your approval." : "Check the private checkpoint before any cleanup."} ${!d.photos.subscriptionChanged ? "Google One unchanged." : ""}`
          : "Checkpoint unavailable.",
      ),
      element("p", `Checkpoint updated ${format(d.photos?.updatedAt)}`, "meta"),
    );
    $("sources").replaceChildren(
      element(
        "p",
        `Source collection completed ${format(d.sourceCollectedAt)}. Successful collection does not prove upstream sync; coverage in the brief still applies.`,
        "meta",
      ),
    );
    for (const s of d.sources || []) {
      const row = element("div", undefined, "source");
      row.append(
        element("span", names[s.name] || s.name),
        element(
          "span",
          `${s.state} · ${format(s.collectedAt || s.attemptedAt)}`,
        ),
      );
      $("sources").append(row);
    }
    $("health").replaceChildren(
      element(
        "p",
        d.health?.scope ||
          "Local homelab-dev services only; status unavailable.",
        "meta",
      ),
    );
    if (!Object.keys(d.health?.services || {}).length)
      $("health").append(element("p", "No local service statuses available."));
    for (const [unit, h] of Object.entries(d.health?.services || {})) {
      const row = element("div", undefined, "source");
      row.append(
        element("span", unit.replace("agent-", "")),
        element(
          "span",
          `${h.ActiveState} / ${h.SubState || "unknown"}${h.Result ? ` · last result: ${h.Result}` : ""}`,
        ),
      );
      $("health").append(row);
    }
  } catch {
    $("notice").hidden = false;
    $("notice").textContent =
      "Could not reach the dashboard. Check your tailnet connection and refresh. Any displayed brief is from the last successful load.";
  } finally {
    $("refresh").disabled = false;
  }
}

const berlinDayFormatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
const dayKey = (value) => berlinDayFormatter.format(new Date(value));
const dateOf = (key) => new Date(`${key}T12:00:00Z`);
const shift = (key, days) => {
  const d = dateOf(key);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
};
const dayLabel = (key, options = { dateStyle: "full" }) =>
  new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Berlin",
    ...options,
  }).format(dateOf(key));
const categories = {
  own: "Own",
  club: "Club",
  study: "Study",
  shared: "Shared context",
  garmin: "Garmin history",
};
let dashboard = {},
  selected = dayKey(new Date()),
  anchor = selected,
  view = "week";
const enabled = new Set(Object.keys(categories));
for (const [key, label] of Object.entries(categories)) {
  const wrapper = element("label", undefined, `filter ${key}`);
  const input = element("input");
  input.type = "checkbox";
  input.checked = true;
  input.value = key;
  input.addEventListener("change", () => {
    input.checked ? enabled.add(key) : enabled.delete(key);
    renderCalendar();
  });
  wrapper.append(input, document.createTextNode(label));
  $("calendar-filters").append(wrapper);
}
function events() {
  const entries = [...(dashboard.calendar?.events || [])];
  for (const a of dashboard.garmin?.data?.activities?.data || []) {
    const start =
      a.startTimeGMT &&
      (/Z$|[+]\d\d:\d\d$/.test(a.startTimeGMT)
        ? a.startTimeGMT
        : a.startTimeGMT + "Z");
    if (!start || !Number.isFinite(Date.parse(start))) continue;
    entries.push({
      title: a.name,
      start,
      category: "garmin",
      kind: "activity",
      source: "Garmin recorded activity",
      durationSeconds: a.durationSeconds,
      distanceMeters: a.distanceMeters,
      observedAt: a.startTimeGMT,
    });
  }
  return entries
    .filter((e) => enabled.has(e.category))
    .sort(
      (a, b) =>
        String(a.start).localeCompare(String(b.start)) ||
        String(a.title).localeCompare(String(b.title)),
    );
}
function onDay(e, key) {
  if (!e.start) return false;
  const start = e.allDay ? e.start.slice(0, 10) : dayKey(e.start);
  if (!e.end || e.end <= e.start) return start === key;
  // Calendar end is exclusive, including all-day and midnight endings.
  const last = e.allDay
    ? shift(e.end.slice(0, 10), -1)
    : dayKey(new Date(Date.parse(e.end) - 1));
  return start <= key && key <= last;
}
function eventTime(e, key) {
  if (e.allDay) return e.kind === "deadline" ? "Due" : "All day";
  if (dayKey(e.start) !== key) return "Continues";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Berlin",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(e.start));
}
function covered(key) {
  const c = dashboard.calendar;
  return (
    c?.range &&
    c.state !== "unavailable" &&
    c.range.start <= key &&
    key < c.range.end
  );
}
function dailySummary(text) {
  const root = $("priorities");
  root.replaceChildren();
  if (!text) {
    root.append(
      element(
        "p",
        "No brief published. The daily writeup appears after successful collection and synthesis.",
      ),
    );
    return;
  }
  // A short excerpt of the synthesized edition; keep the full report and citations intact.
  const sections = text.split(/\n(?=#{1,6}\s|\*\*[^*]+\*\*\s*$)/m);
  const substantive = sections.filter((s) =>
    s.split("\n").some((line) => line.trim() && !/^(#{1,6}\s|\*\*[^*]+\*\*\s*$)/.test(line)),
  );
  const main =
    substantive.find((s) => /actions|priorities/i.test(s.split("\n")[0])) ||
    substantive.find((s) => !/coverage|limitations|sources/i.test(s.split("\n")[0])) ||
    substantive[0] || "";
  const lines = main
    .split("\n")
    .filter((l) => l.trim() && !/^(#{1,6}\s|\*\*[^*]+\*\*\s*$)/.test(l));
  report(lines.slice(0, 3).join("\n"), root);
  if (!root.textContent.trim())
    root.append(
      element("p", "See the full edition below for today’s synthesis."),
    );
}
function renderCalendar() {
  const c = dashboard.calendar;
  const root = $("calendar-grid");
  root.replaceChildren();
  root.className = `calendar-grid ${view}`;
  const first = view === "month" ? anchor.slice(0, 7) + "-01" : anchor;
  const weekday = (dateOf(first).getUTCDay() + 6) % 7;
  const start = shift(first, -weekday);
  const end =
    view === "week"
      ? shift(start, 7)
      : (() => {
          const d = dateOf(first);
          d.setUTCMonth(d.getUTCMonth() + 1);
          const k = d.toISOString().slice(0, 10);
          return shift(k, (7 - ((dateOf(k).getUTCDay() + 6) % 7)) % 7);
        })();
  $("calendar-period").textContent =
    view === "month"
      ? dayLabel(first, { month: "long", year: "numeric" })
      : `${dayLabel(start, { day: "numeric", month: "short" })} – ${dayLabel(shift(end, -1), { day: "numeric", month: "short", year: "numeric" })}`;
  $("go-date").value = selected;
  for (const v of ["week", "month"])
    $(v + "-view").setAttribute("aria-pressed", String(v === view));
  $("previous").setAttribute("aria-label", `Previous ${view}`);
  $("next").setAttribute("aria-label", `Next ${view}`);
  const state = c?.state || "not collected";
  $("calendar-coverage").textContent = c?.range
    ? `${state}${c.partial ? " · Partial coverage" : ""}. Calendar range ${c.range.start} to ${shift(c.range.end, -1)}. Collected ${format(c.collectedAt || c.attemptedAt)}. ${c.cache || ""} ${(c.limitations || []).join(" ")}`
    : "Calendar coverage unavailable. Refresh reloads the published edition; it does not sync accounts.";
  const all = events(),
    today = dayKey(new Date());
  for (let key = start; key < end; key = shift(key, 1)) {
    const day = element("button", undefined, "calendar-day");
    day.type = "button";
    day.dataset.date = key;
    day.classList.toggle("selected", key === selected);
    day.classList.toggle("today", key === today);
    day.classList.toggle("outside", !covered(key));
    if (view === "month")
      day.classList.toggle(
        "other-month",
        key.slice(0, 7) !== anchor.slice(0, 7),
      );
    day.setAttribute("aria-pressed", String(key === selected));
    day.setAttribute("aria-label", dayLabel(key));
    const heading = element("span", undefined, "day-heading");
    heading.append(
      element("span", dayLabel(key, { weekday: "short" })),
      element("strong", String(Number(key.slice(-2)))),
    );
    day.append(heading);
    const entries = all.filter((e) => onDay(e, key));
    for (const e of entries.slice(0, view === "month" ? 3 : 8))
      day.append(
        element(
          "span",
          `${eventTime(e, key)} ${e.title}`,
          `calendar-event ${e.category}`,
        ),
      );
    if (entries.length > (view === "month" ? 3 : 8))
      day.append(
        element(
          "span",
          `+${entries.length - (view === "month" ? 3 : 8)} more`,
          "more-events",
        ),
      );
    if (!entries.length)
      day.append(
        element(
          "span",
          covered(key)
            ? c.partial || c.state !== "ok"
              ? "No events returned · partial"
              : enabled.size === 5
                ? "No events"
                : "No matching events"
            : "Outside coverage",
          "empty-day",
        ),
      );
    const chosen = key;
    day.addEventListener("click", () => {
      selected = chosen;
      renderCalendar();
    });
    root.append(day);
  }
  $("selected-date").textContent = dayLabel(selected, {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
  const agenda = $("selected-agenda");
  agenda.replaceChildren();
  const entries = all.filter((e) => onDay(e, selected));
  if (!covered(selected))
    agenda.append(
      element(
        "p",
        "Calendar coverage unavailable for this date. This does not mean the day is free.",
        "coverage-warning",
      ),
    );
  else if (c.partial || c.state !== "ok")
    agenda.append(
      element(
        "p",
        "Partial calendar results. Other events may be missing.",
        "coverage-warning",
      ),
    );
  if (!entries.length)
    agenda.append(
      element(
        "p",
        covered(selected)
          ? "No events match the selected sources."
          : "No recorded entries available.",
      ),
    );
  for (const e of entries) {
    const item = element("div", undefined, `agenda-event ${e.category}`);
    item.append(
      element(
        "p",
        `${eventTime(e, selected)} · ${categories[e.category] || e.category}`,
        "meta",
      ),
      element("h3", e.title),
    );
    if (e.end && !e.allDay)
      item.append(element("p", `Until ${format(e.end)}`, "meta"));
    if (e.category === "shared" || e.ownership === "partner")
      item.append(
        element("p", "Shared partner context — not your attendance."),
      );
    if (e.ownership === "unconfirmed")
      item.append(
        element("p", "Ownership unconfirmed; not a confirmed commitment."),
      );
    if (e.confirmation)
      item.append(element("p", e.confirmation, "coverage-warning"));
    item.append(element("p", e.source || e.calendar || "Calendar", "meta"));
    if (e.durationSeconds != null)
      item.append(
        element(
          "p",
          `${Math.round(e.durationSeconds / 60)} min${e.distanceMeters == null ? "" : ` · ${(e.distanceMeters / 1000).toFixed(1)} km`}`,
        ),
      );
    agenda.append(item);
  }
  const undated = (c?.undatedTasks || []).filter((t) =>
    enabled.has(t.category),
  );
  if (undated.length) {
    const details = element("details");
    details.append(
      element("summary", `Tasks without dates (${undated.length})`),
    );
    for (const t of undated) details.append(element("p", t.title));
    agenda.append(details);
  }
}
function github(g) {
  const root = $("github");
  root.replaceChildren();
  root.append(
    element(
      "p",
      `${g?.state || "Not collected"} · ${format(g?.collectedAt || g?.attemptedAt)}`,
      "meta",
    ),
  );
  const more = element("details");
  more.append(
    element(
      "summary",
      `More GitHub items (${Math.max(0, (g?.items?.length || 0) - 6)})`,
    ),
  );
  for (const [index, item] of (g?.items || []).entries()) {
    const p = element("p");
    if (/^https:\/\/github\.com\//.test(item.url || "")) {
      const a = element("a", item.title);
      a.href = item.url;
      a.target = "_blank";
      a.rel = "noreferrer noopener";
      p.append(a);
    } else p.append(document.createTextNode(item.title || "Untitled"));
    p.append(element("small", ` ${item.kind || ""} ${item.repository || ""}`));
    (index < 6 ? root : more).append(p);
  }
  if ((g?.items?.length || 0) > 6) root.append(more);
  if (!g?.items?.length)
    root.append(
      element(
        "p",
        "No items returned. Source coverage determines which activity is visible.",
      ),
    );
  for (const limit of g?.limitations || [])
    root.append(element("p", limit, "meta"));
}
function move(direction) {
  if (view === "week") anchor = shift(anchor, direction * 7);
  else {
    const d = dateOf(anchor.slice(0, 7) + "-01");
    d.setUTCMonth(d.getUTCMonth() + direction);
    anchor = d.toISOString().slice(0, 10);
  }
  selected = anchor;
  renderCalendar();
}
$("previous").addEventListener("click", () => move(-1));
$("next").addEventListener("click", () => move(1));
$("today").addEventListener("click", () => {
  anchor = selected = dayKey(new Date());
  renderCalendar();
});
for (const v of ["week", "month"])
  $(v + "-view").addEventListener("click", () => {
    view = v;
    anchor = selected;
    renderCalendar();
  });
$("go-date").addEventListener("change", (e) => {
  if (/^\d{4}-\d{2}-\d{2}$/.test(e.target.value)) {
    anchor = selected = e.target.value;
    renderCalendar();
  }
});
$("read-brief").addEventListener("click", () => {
  $("full-brief").open = true;
});
function clock() {
  $("clock").textContent = format(new Date().toISOString());
  $("date").textContent = dayLabel(dayKey(new Date()));
}
clock();
setInterval(clock, 60000);
$("refresh").addEventListener("click", load);
load();
