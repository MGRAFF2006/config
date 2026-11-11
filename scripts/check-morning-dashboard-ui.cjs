const { chromium } = require(
  process.env.MORNING_PLAYWRIGHT_MODULE || "playwright",
);
const assert = require("node:assert/strict");
(async () => {
  require("node:fs").mkdirSync(
    process.env.HOME + "/.local/state/agent-life/dashboard-verification",
    { recursive: true, mode: 0o700 },
  );
  // mkdir's mode does not tighten a verification directory from an earlier run.
  require("node:fs").chmodSync(
    process.env.HOME + "/.local/state/agent-life/dashboard-verification",
    0o700,
  );
  const browser = await chromium.launch({
    executablePath: process.env.MORNING_BROWSER || "/usr/bin/chromium",
    headless: true,
    args: process.env.MORNING_TAILSCALE_IP
      ? [
          "--host-resolver-rules=MAP homelab-dev.tail03caec.ts.net " +
            process.env.MORNING_TAILSCALE_IP,
        ]
      : [],
  });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    async function refresh() {
      await page.getByRole("button", { name: "Refresh", exact: true }).click();
      await page.waitForFunction(() => !document.getElementById("refresh").disabled);
    }
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const [name, width, height] of [
      ["desktop", 1440, 1100],
      ["mobile", 390, 844],
    ]) {
      await page.setViewportSize({ width, height });
      await page.goto("https://homelab-dev.tail03caec.ts.net/morning/", {
        waitUntil: "networkidle",
      });
      await page.locator("#garmin .status").waitFor();
      await page.keyboard.press("Tab");
      assert.equal(await page.locator(".skip").evaluate((e) => e === document.activeElement), true);
      await page.keyboard.press("Enter");
      assert.equal(await page.locator("#overview").evaluate((e) => e === document.activeElement), true);
      assert.equal(await page.locator(".metrics > div").count(), 6);
      assert.equal(await page.locator("#full-brief").getAttribute("open"), null);
      assert.ok(await page.locator("#priorities").innerText().then((s) => s.length > 20));
      assert.ok(await page.locator("#agenda h2").count() > 0);
      await page.locator("#full-brief > summary").click();
      assert.match(
        await page.locator("#photos").innerText(),
        /Backup verified/,
      );
      assert.match(await page.locator("#photos").innerText(), /paused/);
      assert.ok(
        await page
          .locator("#report")
          .innerText()
          .then((x) => x.length > 100),
      );
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      );
      await page.locator("#full-brief > summary").click();
      await page.screenshot({
        path: `${process.env.HOME}/.local/state/agent-life/dashboard-verification/${name}.png`,
        fullPage: true,
      });
      await page.locator("#coverage").evaluate((e) => (e.open = true));
      await refresh();
      await page.waitForLoadState("networkidle");
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      );
      console.log(
        name,
        "HTTPS loaded; overview/six readings/collapsed original/photo/refresh/expanded coverage/no horizontal overflow passed",
      );
    }
    await page.route("**/morning/data", (r) =>
      r.fulfill({
        json: {
          error: "No published brief available.",
          report: null,
          health: { scope: "Local services only", services: {} },
        },
      }),
    );
    await refresh();
    await page.locator("#priorities").getByText(/No brief published/).waitFor();
    assert.equal(await page.locator(".metrics > div").count(), 6);
    assert.match(await page.locator("#priorities").innerText(), /No brief published/);
    console.log("empty edition state passed");
    await page.unroute("**/morning/data");
    await page.route("**/morning/data", (r) =>
      r.fulfill({
        json: {
          date: "2000-01-01",
          sourceCollectedAt: "2000-01-01T00:00:00Z",
          report:
            "**Actions and changes**\n- <img src=x onerror=alert(1)>\n- [unsafe](javascript:alert(1))\n- Hidden third action [source](https://example.com)\n\n**Explicit university deadlines**\n- Optional opportunity, not an obligation.\n\n**Coverage:** Calendar cache has no sync time.",
          sources: [{ name: "mail", state: "unavailable" }],
          garmin: { state: "unavailable" },
          health: { scope: "Local only", services: {} },
        },
      }),
    );
    await refresh();
    await page.getByText(/This is an older brief/).waitFor();
    assert.equal(await page.locator("#overview img").count(), 0);
    assert.equal(await page.locator("#overview a").count(), 1);
    assert.match(await page.locator("#report-limits").innerText(), /no sync time/);
    assert.match(await page.locator("#agenda").innerText(), /not an obligation/);
    await page.locator("#priorities .more-items > summary").click();
    await page.getByText("Hidden third action", { exact: false }).first().waitFor();
    assert.equal(await page.locator("#report img").count(), 0);
    assert.equal(await page.locator("#report a").count(), 1);
    console.log(
      "stale/partial/error and untrusted markup execution checks passed",
    );
    await page.unroute("**/morning/data");
    await page.route("**/morning/data", (r) => r.fulfill({json: {
      date: "2000-01-01", report: "## Actions\n- A retained priority",
      garmin: {state: "partial", data: {
        sleep: {state: "ok", data: {seconds: 24000, score: 81}},
        daily: {state: "unavailable"}, hrv: {state: "empty"}
      }}, health: {scope: "Local only", services: {"fixture.service": {ActiveState: "failed", SubState: "failed", Result: "exit-code"}}}
    }}));
    await refresh();
    assert.match(await page.locator("#garmin").innerText(), /Partial data/);
    assert.equal(await page.locator(".metrics dd").filter({hasText: "—"}).count(), 4);
    assert.match(await page.locator("#health").innerText(), /failed/);
    console.log("partial readings preserve nulls; failed local unit remains visible");
    await page.unroute("**/morning/data");
    await page.route("**/morning/data", (r) => r.fulfill({status: 503}));
    await refresh();
    await page.getByText(/Could not reach the dashboard/).waitFor();
    assert.match(await page.locator("#priorities").innerText(), /A retained priority/);
    await page.unroute("**/morning/data");
    await page.route("**/morning/data", (r) => r.abort());
    await refresh();
    await page.getByText(/Could not reach the dashboard/).waitFor();
    assert.deepEqual(errors, []);
    console.log("network failure retained displayed report; no browser errors");
    await context.close();
  } finally {
    await browser.close();
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
