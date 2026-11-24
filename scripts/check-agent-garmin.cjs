#!/usr/bin/env node
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { collectGarmin } = require("./agent-garmin.cjs");

test("Bounded official history, UTC activity dates, allowlist and missing-value semantics", async () => {
  const calls = [];
  const result = await collectGarmin({
    key: "private-fixture-key",
    date: "2026-11-18",
    fetchImpl: async (url, options) => {
      calls.push(url);
      if (url.endsWith("/token")) {
        assert.equal(options.headers.Accept, undefined);
        return new Response("private-fixture-token\n");
      }
      if (url.includes("/activities?"))
        return Response.json([
          {
            activityName: "Evening activity",
            startTimeGMT: "2026-11-17 23:30:00",
            duration: 1800,
            distance: -1,
            averageHR: 110,
            activityType: { typeKey: "running" },
            activityUUID: "PRIVATE",
            startLatitude: 12,
            signedUrl: "SECRET",
          },
        ]);
      if (url.includes("/dailySleepSummaries"))
        return Response.json([
          { calendarDate: "2026-11-04", sleepTimeSeconds: 999 },
          {
            calendarDate: "2026-11-05",
            sleepTimeSeconds: 25200,
            userNote: "PRIVATE",
            sleepEndTimestampGMT: 1793862000000,
          },
        ]);
      if (url.includes("/stats/steps/"))
        return Response.json([
          {
            calendarDate: "2026-11-05",
            totalSteps: 0,
            totalDistance: 0,
            stepGoal: 10000,
          },
        ]);
      if (url.includes("/dailySleep"))
        return Response.json({
          calendarDate: "2026-11-18",
          sleepTimeSeconds: 21600,
        });
      if (url.includes("/usersummary/"))
        return Response.json({
          calendarDate: "2026-11-18",
          averageStressLevel: -1,
          activeKilocalories: 0,
          totalSteps: 0,
          wellnessEndTimeGmt: "2026-11-18T04:00:00.000Z",
        });
      return new Response("", { status: 503 });
    },
  });
  assert.equal(calls.length, 7); // One token and six bounded data requests.
  assert.ok(
    calls.some(
      (url) =>
        url.includes("limit=100") &&
        url.includes("startDate=2026-10-19&endDate=2026-11-18"),
    ),
  );
  assert.equal(
    result.data.activities.data[0].startTimeGMT,
    "2026-11-17T23:30:00.000Z",
  );
  assert.equal(result.data.activities.data[0].date, "2026-11-18");
  assert.equal(result.data.activities.data[0].distanceMeters, null);
  assert.equal(result.data.daily.data.stressAverage, null);
  assert.equal(result.data.daily.data.activeKilocalories, 0);
  assert.equal(result.data.daily.data.steps, 0);
  assert.deepEqual(result.data.stepsHistory.data, [
    { date: "2026-11-05", steps: 0, distanceMeters: 0 },
  ]);
  assert.equal(result.data.sleepHistory.data.length, 1);
  assert.equal(result.data.sleepHistory.data[0].date, "2026-11-05");
  assert.equal(result.data.hrv.state, "unavailable");
  assert.ok(result.data.hrv.requestedAt);
  assert.deepEqual(result.data.hrv.requestedRange, {
    start: "2026-11-18",
    end: "2026-11-18",
  });
  assert.doesNotMatch(
    JSON.stringify(result),
    /PRIVATE|SECRET|private-fixture|startLatitude|stepGoal|userNote/,
  );
});

test("Activity cap is reported as partial and malformed timestamps never become dates", async () => {
  const result = await collectGarmin({
    key: "fixture",
    date: "2026-11-18",
    fetchImpl: async (url) => {
      if (url.endsWith("/token")) return new Response("token");
      if (url.includes("/activities?"))
        return Response.json(
          Array.from({ length: 101 }, () => ({
            activityName: "https://secret.invalid/?token=secret",
            startTimeGMT: "invalid",
            distance: 0,
          })),
        );
      return new Response(null, { status: 204 });
    },
  });
  assert.equal(result.data.activities.state, "partial");
  assert.equal(result.data.activities.truncated, true);
  assert.equal(result.data.activities.data.length, 100);
  assert.equal(result.data.activities.data[0].date, null);
  assert.equal(result.data.activities.observedRange, null);
  assert.equal(result.data.sleep.state, "no_data");
  assert.equal(result.data.sleep.data.seconds, null);
  assert.doesNotMatch(JSON.stringify(result), /secret/);
});

test("Publisher reprojects a poisoned Garmin snapshot with bounded health allowlists", () => {
  const { projectGarmin } = require("./agent-morning-dashboard.cjs");
  const at = "2026-11-18T05:00:00.000Z";
  const range = { start: "2026-11-05", end: "2026-11-18", token: "TOP_SECRET" };
  const endpoint = {
    state: "ok",
    source: "TOP_SECRET",
    requestedAt: at,
    collectedAt: at,
    requestedRange: range,
    observedRange: range,
    repair: "TOP_SECRET",
    accessToken: "TOP_SECRET",
  };
  const projected = projectGarmin({
    state: "ok",
    date: "2026-11-18",
    collectedAt: at,
    activityRange: range,
    historyRange: range,
    profileId: "TOP_SECRET",
    token: "TOP_SECRET",
    data: {
      daily: {
        ...endpoint,
        data: {
          date: "2026-11-18",
          steps: 0,
          restingHeartRate: 55,
          observedAt: at,
          userProfilePK: "TOP_SECRET",
          signedUrl: "https://private.invalid/TOP_SECRET",
        },
      },
      activities: {
        ...endpoint,
        data: [
          {
            name: "Activity https://private.invalid/TOP_SECRET?token=TOP_SECRET",
            date: "2026-11-18",
            startTimeGMT: at,
            durationSeconds: 123,
            uuid: "TOP_SECRET",
            startLatitude: 50,
            downloadUrl: "TOP_SECRET",
          },
        ],
      },
      sleepHistory: {
        ...endpoint,
        data: Array.from({ length: 15 }, () => ({
          date: "2026-11-18",
          seconds: 20000,
          score: 80,
          observedAt: at,
          userNote: "TOP_SECRET",
        })),
      },
      stepsHistory: {
        ...endpoint,
        data: [
          {
            date: "2026-11-18",
            steps: 0,
            distanceMeters: 0,
            stepGoal: "TOP_SECRET",
          },
        ],
      },
      arbitraryEndpoint: { data: { token: "TOP_SECRET" } },
    },
  });
  assert.doesNotMatch(
    JSON.stringify(projected),
    /TOP_SECRET|profileId|signedUrl|downloadUrl|arbitraryEndpoint|userNote|stepGoal|startLatitude/,
  );
  assert.equal(projected.data.daily.data.steps, 0);
  assert.equal(projected.data.daily.data.restingHeartRate, 55);
  assert.equal(projected.data.daily.data.bodyBattery, null);
  assert.equal(projected.data.activities.data[0].durationSeconds, 123);
  assert.equal(projected.data.sleepHistory.data.length, 14);
  assert.equal(projected.data.stepsHistory.data[0].distanceMeters, 0);
  assert.deepEqual(projected.data.daily.requestedRange, {
    start: "2026-11-05",
    end: "2026-11-18",
  });
  assert.equal(projected.data.daily.source, "Garmin Personal API");
  assert.equal(projected.data.daily.requestedAt, at);
});
