const { chromium } = require(
  process.env.MORNING_PLAYWRIGHT_MODULE || "playwright",
);
const assert = require("node:assert/strict");
(async () => {
  require("node:fs").mkdirSync(
    process.env.HOME + "/.local/state/agent-life/dashboard-verification",
    { recursive: true, mode: 0o700 },
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
      await page.getByText("Not connected", { exact: true }).waitFor();
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
      await page.screenshot({
        path: `${process.env.HOME}/.local/state/agent-life/dashboard-verification/${name}.png`,
        fullPage: true,
      });
      await page.locator("#coverage").evaluate((e) => (e.open = true));
      await page.getByRole("button", { name: "Refresh", exact: true }).click();
      await page.waitForLoadState("networkidle");
      assert.ok(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      );
      console.log(
        name,
        "HTTPS loaded; report/photo/missing Garmin/refresh/expanded coverage/no horizontal overflow passed",
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
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await page
      .getByRole("heading", { name: "No brief published", exact: true })
      .waitFor();
    console.log("empty edition state passed");
    await page.unroute("**/morning/data");
    await page.route("**/morning/data", (r) =>
      r.fulfill({
        json: {
          date: "2000-01-01",
          sourceCollectedAt: "2000-01-01T00:00:00Z",
          report:
            "## Actions\n<img src=x onerror=alert(1)>\n[unsafe](javascript:alert(1))",
          sources: [{ name: "mail", state: "unavailable" }],
          garmin: { state: "unavailable" },
          health: { scope: "Local only", services: {} },
        },
      }),
    );
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await page.getByText(/This is an older brief/).waitFor();
    assert.equal(await page.locator("#report img").count(), 0);
    assert.equal(await page.locator("#report a").count(), 0);
    console.log(
      "stale/partial/error and untrusted markup execution checks passed",
    );
    await page.unroute("**/morning/data");
    await page.route("**/morning/data", (r) => r.abort());
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
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
