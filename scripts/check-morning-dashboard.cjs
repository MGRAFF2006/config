#!/usr/bin/env node
const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { collectGarmin } = require("./agent-garmin.cjs");

test("Garmin missing key makes no network call", async () => {
  const result = await collectGarmin({
    key: "",
    fetchImpl: () => {
      throw Error("Must not call");
    },
  });
  assert.equal(result.state, "not_connected");
  assert.ok(result.attemptedAt);
});
test("Official Garmin paths project health data, preserve missing values and isolate endpoint failure", async () => {
  const calls = [];
  const result = await collectGarmin({
    key: "private-test-key",
    date: "2026-11-11",
    fetchImpl: async (url, options) => {
      calls.push([
        new URL(url).pathname + new URL(url).search,
        options.headers.Authorization,
      ]);
      if (url.includes("personal-api-key/token"))
        return new Response(
          JSON.stringify({ access_token: "private-test-token" }),
        );
      if (url.includes("/hrv/")) return new Response("", { status: 503 });
      if (url.includes("/dailySleep"))
        return new Response(
          JSON.stringify({
            calendarDate: "2026-11-11",
            sleepTimeSeconds: 25200,
            sleepScores: { overall: { value: 83 } },
            userProfilePK: "must-not-leak",
          }),
        );
      if (url.includes("/usersummary/"))
        return new Response(
          JSON.stringify({
            calendarDate: "2026-11-11",
            totalSteps: 0,
            bodyBatteryMostRecentValue: 51,
          }),
        );
      return new Response("[]");
    },
  });
  assert.equal(result.state, "partial");
  assert.equal(result.data.sleep.data.seconds, 25200);
  assert.equal(result.data.sleep.data.score, 83);
  assert.equal(result.data.daily.data.steps, 0);
  assert.equal(result.data.daily.data.restingHeartRate, null);
  assert.equal(result.data.hrv.state, "unavailable");
  assert.equal(result.data.activities.state, "no_data");
  assert.ok(
    calls.some(
      ([url]) => url === "/sleep-service/sleep/dailySleep?date=2026-11-11",
    ),
  );
  assert.ok(
    calls.some(
      ([url]) =>
        url ===
        "/usersummary-service/usersummary/daily?calendarDate=2026-11-11",
    ),
  );
  assert.ok(
    calls.slice(1).every(([, auth]) => auth === "Bearer private-test-token"),
  );
  assert.doesNotMatch(JSON.stringify(result), /private-test|must-not-leak/);
});
test("Expired Garmin token response cannot leak API response into report", async () => {
  const result = await collectGarmin({
    key: "test",
    fetchImpl: async () =>
      new Response("sensitive upstream diagnostic", { status: 401 }),
  });
  assert.equal(result.state, "unavailable");
  assert.doesNotMatch(JSON.stringify(result), /sensitive/);
});
test("Publication and HTTP serve only report projection; failed publication retains last good edition", async () => {
  const state = await fs.mkdtemp(path.join(os.tmpdir(), "morning-check-"));
  process.env.MORNING_STATE_DIR = state;
  const { publish, createServer } = require("./agent-morning-dashboard.cjs");
  let server;
  try {
    await fs.writeFile(
      path.join(state, "latest-brief.md"),
      "# Brief\nAction [source](https://example.org/task?token=SECRET)\n",
    );
    await fs.writeFile(
      path.join(state, "snapshot.json"),
      JSON.stringify({
        date: "2026-11-11",
        collectedAt: "2026-11-11T05:00:00Z",
        sources: {
          mail: { state: "ok", data: { body: "RAW MAIL MUST NOT LEAK" } },
          localCalendar: { state: "ok", data: { events: ["PARTNER EVENT"] } },
        },
      }),
    );
    await publish();
    const good = await fs.readFile(path.join(state, "dashboard.json"), "utf8");
    assert.doesNotMatch(good, /SECRET|RAW MAIL|PARTNER EVENT/);
    await fs.writeFile(path.join(state, "latest-brief.md"), "");
    await assert.rejects(publish());
    assert.equal(
      await fs.readFile(path.join(state, "dashboard.json"), "utf8"),
      good,
    );
    server = createServer();
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const base = `http://127.0.0.1:${server.address().port}`;
    for (const route of [
      "/snapshot.json",
      "/brief-prompt.txt",
      "/../snapshot.json",
      "/data/../../brief-prompt.txt",
      "/.config/agent-life/garmin-api-key",
    ])
      assert.equal((await fetch(base + route)).status, 404);
    const response = await fetch(base + "/morning/data");
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.doesNotMatch(await response.text(), /RAW MAIL|PARTNER EVENT/);
    assert.equal((await fetch(base + "/data", { method: "POST" })).status, 405);
  } finally {
    if (server) await new Promise((resolve) => server.close(resolve));
    await fs.rm(state, { recursive: true, force: true });
  }
});
