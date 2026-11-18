// Isolated local source verification by default; set MORNING_URL only for deployed checks.
const { chromium } = require(
  process.env.MORNING_PLAYWRIGHT_MODULE || "playwright",
);
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
(async () => {
  const state = await fs.mkdtemp(path.join(os.tmpdir(), "morning-ui-"));
  process.env.MORNING_STATE_DIR = state;
  const { createServer } = require("./agent-morning-dashboard.cjs");
  const server = createServer();
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const url =
    process.env.MORNING_URL ||
    `http://127.0.0.1:${server.address().port}/morning/`;
  const browser = await chromium.launch({
    executablePath: process.env.MORNING_BROWSER || "/usr/bin/chromium",
    headless: true,
  });
  const dir = path.join(
    os.homedir(),
    ".local/state/agent-life/dashboard-verification",
  );
  await fs.mkdir(dir, { recursive: true, mode: 0o700 });
  await fs.chmod(dir, 0o700);
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    const fixture = {
      date: "2000-01-01",
      sourceCollectedAt: "2000-01-01T05:00:00Z",
      reportUpdatedAt: "2000-01-01T05:00:00Z",
      report:
        "## Actions\n- Review today’s work [source](https://github.com/example/repo/issues/1)\n- <img src=x onerror=alert(1)>\n\nCoverage: Calendar is cached.",
      sources: [{ name: "calendar", state: "partial" }],
      calendar: {
        state: "ok",
        range: { start: "2026-10-01", end: "2027-01-01" },
        cache: "Client cache; upstream sync unknown",
        events: [
          {
            title: "Own event",
            start: "2026-11-18T09:00:00+01:00",
            end: "2026-11-18T10:00:00+01:00",
            category: "own",
          },
          {
            title: "Simultaneous study",
            start: "2026-11-18T09:00:00+01:00",
            category: "study",
          },
          {
            title: "Partner context",
            start: "2026-11-18",
            end: "2026-11-20",
            allDay: true,
            category: "shared",
            ownership: "partner",
          },
          {
            title: "<script>unsafe</script>",
            start: "2026-11-18",
            allDay: true,
            category: "club",
          },
        ],
      },
      garmin: {
        state: "partial",
        historyRange: { start: "2026-11-05", end: "2026-11-18" },
        data: {
          sleepHistory: {
            state: "ok",
            data: [{ date: "2026-11-17", seconds: 25200, score: 80 }],
          },
          stepsHistory: {
            state: "ok",
            data: [{ date: "2026-11-17", steps: 0 }],
          },
          sleep: { state: "ok", data: { seconds: 24000, score: 81 } },
          activities: {
            state: "ok",
            data: [
              {
                name: "Recorded run",
                startTimeGMT: "2026-11-18T06:00:00Z",
                durationSeconds: 1800,
              },
            ],
          },
        },
      },
      health: {
        scope: "Local only",
        services: {
          "fixture.service": {
            ActiveState: "failed",
            SubState: "failed",
            Result: "exit-code",
          },
        },
      },
    };
    let data = fixture;
    await page.route("**/morning/data", (r) => r.fulfill({ json: data }));
    async function refresh() {
      await page.getByRole("button", { name: "Refresh", exact: true }).click();
      await page.waitForFunction(
        () => !document.getElementById("refresh").disabled,
      );
    }
    async function choose(date) {
      await page.locator("#go-date").fill(date);
      await page.locator("#go-date").dispatchEvent("change");
    }
    for (const [name, width, height] of [
      ["desktop", 1440, 1000],
      ["mobile", 390, 844],
    ]) {
      await page.setViewportSize({ width, height });
      await page.goto(url, { waitUntil: "networkidle" });
      await page.locator("#calendar-grid .calendar-day").first().waitFor();
      await page.keyboard.press("Tab");
      assert.equal(
        await page
          .locator(".skip")
          .evaluate((e) => e === document.activeElement),
        true,
      );
      await page.keyboard.press("Enter");
      assert.equal(
        await page
          .locator("#overview")
          .evaluate((e) => e === document.activeElement),
        true,
      );
      // Stale edition must not set current date or initial calendar selection.
      assert.doesNotMatch(await page.locator("#date").innerText(), /2000/);
      assert.match(await page.locator("#notice").innerText(), /older brief/);
      await choose("2026-11-18");
      await page.locator("#garmin-history summary").click();
      assert.match(
        await page.locator("#garmin-history tbody").innerText(),
        /2026-11-17.*7.0 h.*80.*0/s,
      );
      await page.locator("#garmin-history summary").click();
      await page.locator("#read-brief").click();
      assert.equal(await page.locator("#full-brief").getAttribute("open"), "");
      assert.equal(await page.locator("#report img").count(), 0);
      await page.locator("#full-brief summary").click();
      assert.equal(
        await page.locator(".calendar-day.selected").getAttribute("data-date"),
        "2026-11-18",
      );
      assert.match(
        await page.locator("#selected-agenda").innerText(),
        /Own event/,
      );
      assert.match(
        await page.locator("#selected-agenda").innerText(),
        /Simultaneous study/,
      );
      assert.match(
        await page.locator("#selected-agenda").innerText(),
        /not your attendance/,
      );
      assert.match(
        await page.locator("#selected-agenda").innerText(),
        /Recorded run/,
      );
      assert.equal(
        await page.locator("#overview script, #overview img").count(),
        0,
      );
      await page.locator('input[value="shared"]').uncheck();
      assert.doesNotMatch(
        await page.locator("#selected-agenda").innerText(),
        /Partner context/,
      );
      await page.locator('input[value="shared"]').check();
      await page.getByRole("button", { name: "Month", exact: true }).click();
      assert.ok((await page.locator(".calendar-day").count()) >= 28);
      await page
        .getByRole("button", { name: "Next month", exact: true })
        .click();
      assert.match(
        await page.locator("#calendar-period").innerText(),
        /December 2026/,
      );
      await page
        .getByRole("button", { name: "Previous month", exact: true })
        .click();
      await page.locator('[data-date="2026-11-19"]').click();
      assert.match(
        await page.locator("#selected-agenda").innerText(),
        /Partner context/,
      );
      await page.locator('[data-date="2026-11-20"]').click();
      assert.doesNotMatch(
        await page.locator("#selected-agenda").innerText(),
        /Partner context/,
      );
      assert.match(
        await page.locator("#selected-agenda").innerText(),
        /No events match/,
      );
      await choose("2027-03-01");
      assert.match(
        await page.locator("#selected-agenda").innerText(),
        /does not mean the day is free/,
      );
      await choose("2026-11-18");
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      );
      await page.screenshot({
        path: path.join(dir, `calendar-${name}.png`),
        fullPage: true,
      });
      await page.getByRole("button", { name: "Week", exact: true }).click();
      await page.getByRole("button", { name: "Today", exact: true }).click();
      assert.equal(
        await page.locator(".calendar-day.selected").getAttribute("data-date"),
        await page.evaluate(() =>
          new Intl.DateTimeFormat("en-CA", {
            timeZone: "Europe/Berlin",
          }).format(new Date()),
        ),
      );
    }
    data = {
      ...fixture,
      calendar: {
        ...fixture.calendar,
        state: "partial",
        partial: true,
        events: [],
      },
    };
    await refresh();
    await choose("2026-11-18");
    assert.match(
      await page.locator("#selected-agenda").innerText(),
      /Partial calendar results/,
    );
    data = { report: null, calendar: { state: "unavailable" } };
    await refresh();
    assert.match(
      await page.locator("#priorities").innerText(),
      /No brief published/,
    );
    assert.match(
      await page.locator("#calendar-coverage").innerText(),
      /unavailable/,
    );
    data = fixture;
    await refresh();
    assert.match(await page.locator("#health").innerText(), /failed/);
    await page.unroute("**/morning/data");
    await page.route("**/morning/data", (r) => r.fulfill({ status: 503 }));
    await refresh();
    assert.match(await page.locator("#notice").innerText(), /Could not reach/);
    assert.match(await page.locator("#priorities").innerText(), /Review today/);
    assert.deepEqual(errors, []);
    await context.close();
    console.log(
      "Local source UI: desktop/mobile, week/month/date/today, filters, simultaneous/all-day boundaries, stale/partial/empty/error, safe rendering and retained refresh passed. Private screenshots:",
      dir,
    );
  } finally {
    await browser.close();
    await new Promise((r) => server.close(r));
    await fs.rm(state, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
