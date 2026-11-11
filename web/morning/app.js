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
    const heading = line.match(/^(#{1,6})\s+(.+)/) ||
      line.match(/^(\*\*)([^*]+)\*\*$/);
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
    const heading = line.match(/^#{1,6}\s+(.+)$/) || line.match(/^\*\*([^*]+)\*\*$/);
    const coverage = line.match(/^\s*(Coverage:|\*\*Coverage:\*\*|\*\*Coverage\*\*:)\s*(.*)$/i);
    if (heading || coverage) {
      current = { title: (heading || coverage)[1], lines: coverage ? [coverage[2]] : [] };
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
    const target = limits ? "report-limits" : priority ? "priorities" :
      /today|deadlines|next seven|upcoming|calendar/i.test(title) ? "agenda" : "followups";
    const node = element("section", undefined, limits ? "" : "report-module");
    node.append(element("h2", title));
    const content = element("div");
    const lines = section.lines;
    // Collapse extra bullets, never discard their text or contextual caveats.
    const bullets = lines.map((line, i) => /^\s*(?:[-*]|\d+\.)\s+/.test(line) ? i : -1).filter((i) => i >= 0);
    const visibleItems = priority ? 1 : 2;
    if (!limits && bullets.length > visibleItems) {
      const cut = bullets[visibleItems];
      report(lines.slice(0, cut).join("\n"), content);
      const rest = element("details", undefined, "more-items");
      rest.append(element("summary", `More from this section (${bullets.length - visibleItems})`));
      const body = element("div");
      report(lines.slice(cut).join("\n"), body);
      rest.append(body);
      content.append(rest);
    } else report(lines.join("\n"), content);
    node.append(content);
    $(target).append(node);
    if (priority) hasPriorities = true;
  }
  if (!hasPriorities) $("priorities").append(element("h2", "Priorities"),
    element("p", text ? "No priorities section in this edition. See the report sections below." : "No brief published. The overview will appear after a successful morning edition."));
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
        `${name}: ${result.state}${result.data?.date ? `; day ${result.data.date}` : ""}; fetched ${format(result.collectedAt || result.attemptedAt)}${result.data?.observedAt ? `; observed ${result.data.observedAt}` : ""}`,
        "meta",
      ),
    );
  }
  const activities = g?.data?.activities?.data;
  const activityRoot = $("activities");
  activityRoot.replaceChildren();
  if (activities?.length) {
    const more = element("details", undefined, "more-items");
    more.append(element("summary", `More activities (${Math.max(0, activities.length - 2)})`));
    for (const [index, a] of activities.entries())
      (index < 2 ? activityRoot : more).append(
        element(
          "p",
          `${a.name} · ${a.startTimeGMT || "Time unavailable"}${a.durationSeconds == null ? "" : ` · ${Math.round(a.durationSeconds / 60)} min`}`,
        ),
      );
    if (activities.length > 2) activityRoot.append(more);
  } else activityRoot.append(element("p", `No recent activities available (${g?.data?.activities?.state || g?.state || "not collected"}).`));
}
async function load() {
  $("refresh").disabled = true;
  try {
    const response = await fetch("/morning/data", { cache: "no-store" });
    if (!response.ok) throw Error("fetch");
    const d = await response.json();
    $("date").textContent = d.date
      ? new Intl.DateTimeFormat("en-GB", {
          timeZone: "Europe/Berlin",
          dateStyle: "full",
        }).format(new Date(`${d.date}T12:00:00+01:00`))
      : "Your morning brief";
    $("freshness").textContent = `Brief prepared ${format(d.reportUpdatedAt)}`;
    const berlinDate = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Europe/Berlin",
    }).format(new Date());
    const stale =
      d.date !== berlinDate ||
      Date.now() - Date.parse(d.sourceCollectedAt) > 24 * 3600000;
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
      element("p", d.health?.scope || "Local homelab-dev services only; status unavailable.", "meta"),
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
$("clock").textContent = format(new Date().toISOString());
$("refresh").addEventListener("click", load);
load();
