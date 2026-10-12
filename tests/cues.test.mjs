import { test } from "node:test";
import assert from "node:assert/strict";
import { cuesAt, locate, pointAt } from "../web/cues.js";

// A straight 400 m route heading east, with seats at 0, 150 and 300 m and a left turn at 200 m.
const lat = 50.0, lon0 = 8.0, mPerDegLon = 111320 * Math.cos((lat * Math.PI) / 180);
const path = [0, 100, 200, 300, 400].map((m) => [lat, lon0 + m / mPerDegLon]);
const route = {
  length_m: 400,
  path,
  cum_m: [0, 100, 200, 300, 400],
  seats: [
    { at_m: 0, kind: "bench" },
    { at_m: 150, kind: "tea_stall_bench", source: "gemma" },
    { at_m: 300, kind: "bench" },
  ],
  turns: [{ at_m: 200, dir: "left" }],
  warnings: [{ at_m: 260, kind: "steps" }],
  toilets: [],
};

function walkAll(step = 5) {
  const said = new Set();
  const spoken = [];
  for (let at = 0; at <= 400; at += step) spoken.push(...cuesAt(route, at, 3, said, at * 1000));
  return spoken;
}

test("start cue names the first seat ahead", () => {
  assert.equal(cuesAt(route, 0, 2, new Set())[0], "Walk started. Tea-stall bench in 150 metres.");
});

test("a whole walk speaks each cue once, in order", () => {
  const spoken = walkAll();
  assert.deepEqual(spoken, [
    "Walk started. Tea-stall bench in 150 metres.",
    "Tea-stall bench here. Rest if you like.",
    "In 30 metres, turn left.",
    "Bench in 100 metres.",
    "Halfway. The way back is just as gentle.",
    "Steps beside the path ahead. Stay on the route, it avoids them.",
    "Bench here. Rest if you like.",
    "Walk complete. Well done.",
  ]);
});

test("a street full of seats does not turn into chatter", () => {
  const dense = { ...route, turns: [], warnings: [],
    seats: [0, 20, 40, 60, 60, 80, 100, 120, 140, 160, 180, 200, 220].map((at_m) => ({ at_m, kind: "platform_or_ledge" })) };
  const said = new Set();
  const spoken = [];
  for (let at = 0; at <= 400; at += 5) spoken.push(...cuesAt(dense, at, 3, said, at * 1000));
  assert.equal(spoken.filter((t) => t.includes(" in ") && !t.startsWith("Walk started")).length, 0, spoken.join(" | "));
  const here = spoken.filter((t) => t.includes("here"));
  assert.ok(here.length >= 4 && here.length <= 6, here.join(" | "));
});

test("off the route: warn, but at most every 30 seconds", () => {
  const said = new Set();
  assert.deepEqual(cuesAt(route, 50, 60, said, 1_000), ["You are off the route. Turn back to the path."]);
  assert.deepEqual(cuesAt(route, 50, 60, said, 20_000), []);
  assert.deepEqual(cuesAt(route, 50, 60, said, 40_000), ["You are off the route. Turn back to the path."]);
});

test("locate snaps a GPS point to the route and measures how far off it is", () => {
  const p = pointAt(route, 120);
  const north10m = [p[0] + 10 / 110540, p[1]];
  const pos = locate(route, north10m, 100);
  assert.ok(Math.abs(pos.at - 120) < 1, `at ${pos.at}`);
  assert.ok(Math.abs(pos.off - 10) < 1, `off ${pos.off}`);
});

test("locate only searches near the last position", () => {
  // From 0 m the window ends at 250 m, so a point at 390 m only matches the 300 m end of the window.
  const pos = locate(route, pointAt(route, 390), 0);
  assert.ok(pos.at <= 300 && pos.off > 80, `at ${pos.at}, off ${pos.off}`);
});
