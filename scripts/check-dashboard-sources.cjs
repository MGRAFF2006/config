#!/usr/bin/env node
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const {
  collectCalendar,
  projectCalendar,
  calendarRange,
  collectGithub,
  projectGithub,
} = require("./agent-dashboard-sources.cjs");
const own = "11111111-1111-4111-8111-111111111111",
  partner = "22222222-2222-4222-8222-222222222222";
const preferences = `Mathis owns: Studium (${own}; physics). His girlfriend owns: Studium (${partner}; chemistry). Ownership of other calendars is unconfirmed.`;
const event = (extra = {}) => ({
  id: "private-event-id",
  calendarId: own,
  calendarName: "Studium",
  title: "Lecture",
  startDate: "2026-11-18T09:00:00Z",
  endDate: "2026-11-18T10:00:00Z",
  ...extra,
});
test("Calendar browsing queries each calendar in three bounded local months and flags caps/errors", async () => {
  const calls = [];
  const data = await collectCalendar(async (name, args) => {
    calls.push([name, args]);
    if (name === "listCalendars")
      return [
        { id: own, name: "Studium", supportsEvents: true },
        { id: partner, name: "Studium", supportsEvents: true },
        { id: "disabled", disabled: true },
        { id: "warning", name: "⚠ warning" },
      ];
    if (args.calendarId === partner) throw Error("Private upstream diagnostic");
    return Array.from({ length: 500 }, (_, i) =>
      event({ id: "id" + i, startDate: args.startDate }),
    );
  }, new Date("2026-11-18T08:00:00Z"));
  assert.deepEqual(data.range, { start: "2026-10-01", end: "2027-01-01" });
  assert.equal(calls.filter(([name]) => name === "listEvents").length, 6);
  assert.equal(calls[1][1].startDate, "2026-09-30T22:00:00.000Z");
  assert.equal(calls[2][1].startDate, "2026-10-31T23:00:00.000Z");
  assert.ok(calls.slice(1).every(([, args]) => args.maxResults === 500));
  const projected = projectCalendar({ state: "ok", data }, preferences);
  assert.equal(projected.state, "partial");
  assert.equal(projected.partial, true);
  assert.doesNotMatch(
    JSON.stringify(projected),
    /Private upstream diagnostic|private-event-id|11111111|22222222|organizer|attendees/,
  );
});
test("Projection preserves simultaneous and all-day spans, ownership, deadlines; excludes raw fields and recurrence masters", () => {
  const result = projectCalendar(
    {
      state: "ok",
      collectedAt: "2026-11-18T05:00:00Z",
      data: {
        range: { start: "2026-10-01", end: "2027-01-01" },
        events: [
          event({
            description: "RAW SECRET",
            organizer: { email: "private@email" },
            onlineMeetingURL: "https://secret/signed",
            allDay: true,
            startDate: "2026-11-18T00:00:00Z",
            endDate: "2026-11-19T00:00:00Z",
          }),
          event({ calendarId: partner }),
          event(),
          event({ recurrenceNotExpanded: true }),
          event({ status: "cancelled" }),
          event({ myParticipationStatus: "DECLINED" }),
        ],
        tasks: [
          event({ dueDate: "2026-11-20T12:00:00Z" }),
          event({ dueDate: null }),
        ],
      },
    },
    preferences,
  );
  assert.equal(result.events.length, 4);
  assert.equal(result.undatedTasks.length, 1);
  assert.equal(result.events[0].start, "2026-11-18");
  assert.equal(result.events[0].end, "2026-11-20");
  assert.equal(result.events[0].ownership, "own");
  assert.equal(result.events[0].category, "study");
  assert.equal(result.events[1].ownership, "partner");
  assert.equal(result.events[1].category, "shared");
  assert.equal(result.events[3].kind, "deadline");
  assert.equal(result.events[2].start, result.events[1].start);
  assert.doesNotMatch(
    JSON.stringify(result),
    /RAW SECRET|private@email|signed|11111111|22222222|private-event-id|recurrenceNotExpanded/,
  );
});
test("Calendar empty range remains different from unavailable/no requested coverage", () => {
  const empty = projectCalendar(
    {
      state: "ok",
      data: {
        range: { start: "2026-10-01", end: "2027-01-01" },
        events: [],
        tasks: [],
      },
    },
    preferences,
  );
  assert.equal(empty.state, "ok");
  assert.ok(empty.range);
  assert.deepEqual(empty.events, []);
  const absent = projectCalendar({ state: "unavailable" }, preferences);
  assert.equal(absent.state, "unavailable");
  assert.equal(absent.range, null);
  assert.deepEqual(absent.events, []);
  assert.deepEqual(calendarRange(new Date("2026-12-31T23:30:00Z")), {
    start: "2026-12-01",
    end: "2027-03-01",
  });
});
test("GitHub projects safe actionable references, deduplicates and exposes inaccessible APIs", async () => {
  const data = await collectGithub(async (_cmd, args) => {
    if (args[1] === "user")
      return { stdout: JSON.stringify({ login: "test-user" }) };
    if (args[1] === "graphql") throw Error("Private auth diagnostic");
    if (args.includes("search/issues"))
      return {
        stdout: JSON.stringify({
          total_count: 31,
          items: [
            {
              title: "Useful PR",
              html_url: "https://github.com/owner/repo/pull/1?token=secret",
              body: "RAW GITHUB BODY",
              updated_at: "2026-11-18T05:00:00Z",
            },
          ],
        }),
      };
    return { stdout: "[]" };
  });
  const result = projectGithub({ state: "ok", data });
  assert.equal(result.state, "partial");
  assert.equal(result.items.length, 1);
  assert.equal(result.items[0].kind, "Review requested");
  assert.equal(result.items[0].url, "https://github.com/owner/repo/pull/1");
  assert.match(result.limitations.join(" "), /projects/);
  assert.match(result.limitations.join(" "), /additional results/);
  assert.doesNotMatch(
    JSON.stringify(result),
    /RAW GITHUB BODY|secret|Private auth diagnostic/,
  );
});
test("GitHub personal projects and safe push references retain dates without raw activity payload", () => {
  const result = projectGithub({
    state: "ok",
    data: {
      results: {
        projects: {
          data: {
            viewer: {
              projectsV2: {
                nodes: [
                  {
                    title: "Work plan",
                    url: "https://github.com/users/test-user/projects/2",
                    updatedAt: "2026-11-18T05:00:00Z",
                  },
                ],
                pageInfo: { hasNextPage: true },
              },
            },
          },
        },
        activity: Array.from({ length: 30 }, () => ({
          type: "PushEvent",
          repo: { name: "owner/repo" },
          created_at: "2026-11-18T07:00:00Z",
          payload: {
            head: "a".repeat(40),
            commits: [{ message: "RAW COMMIT BODY" }],
          },
        })),
        notifications: Array.from({ length: 50 }, () => ({})),
      },
    },
  });
  assert.equal(result.items.length, 2);
  assert.equal(
    result.items[0].url,
    "https://github.com/users/test-user/projects/2",
  );
  assert.equal(result.items[1].kind, "Recent push");
  assert.equal(result.items[1].updatedAt, "2026-11-18T07:00:00.000Z");
  assert.match(result.limitations.join(" "), /30-event cap/);
  assert.match(result.limitations.join(" "), /50-item cap/);
  assert.match(result.limitations.join(" "), /Additional personal projects/);
  assert.doesNotMatch(JSON.stringify(result), /RAW COMMIT BODY/);
});
test("Publication denies arbitrary fields, preference IDs and signed URL paths", async () => {
  const state = await fs.mkdtemp(path.join(os.tmpdir(), "dashboard-sources-"));
  process.env.MORNING_STATE_DIR = state;
  const { publish } = require("./agent-morning-dashboard.cjs");
  try {
    await fs.writeFile(path.join(state, "brief-preferences.txt"), preferences);
    await fs.writeFile(
      path.join(state, "latest-brief.md"),
      `Brief ${own} [signed](https://unknown.test/private/pathSecret?sig=otherSecret) [Moodle](https://moodle.tu-dortmund.de/mod/assign/view.php?id=123&sesskey=secret)`,
    );
    await fs.writeFile(
      path.join(state, "snapshot.json"),
      JSON.stringify({
        date: { private: "RAW TOP DATE" },
        collectedAt: { private: "RAW TOP TIME" },
        sources: {
          "RAW SOURCE NAME": { state: "RAW SOURCE STATE" },
          localCalendar: {
            state: "ok",
            data: {
              range: { start: "2026-10-01", end: "2027-01-01" },
              events: [
                event({
                  description: "RAW MAIL",
                  password: "TOKEN",
                  extra: "ARBITRARY",
                }),
              ],
            },
          },
          photoMigration: {
            collectedAt: { private: "RAW SOURCE TIME" },
            state: { private: "RAW SOURCE STATE" },
            data: {
              updatedAt: { private: "RAW PHOTO TIME" },
              verifiedAt: { private: "RAW PHOTO TIME" },
              backupVerified: true,
              private: "PRIVATE PHOTO FIELD",
            },
          },
        },
      }),
    );
    await publish();
    const output = await fs.readFile(
      path.join(state, "dashboard.json"),
      "utf8",
    );
    assert.doesNotMatch(
      output,
      /11111111|pathSecret|otherSecret|sesskey|RAW MAIL|TOKEN|ARBITRARY|PRIVATE PHOTO FIELD|RAW TOP|RAW SOURCE|RAW PHOTO/,
    );
    assert.match(output, /id=123/);
    assert.match(output, /Lecture/);
  } finally {
    await fs.rm(state, { recursive: true, force: true });
  }
});
