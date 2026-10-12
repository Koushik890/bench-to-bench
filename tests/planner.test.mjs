import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { attachPoints, buildGraph, classify, parse, planWalks } from "../web/planner.js";

// 6 x 6 grid of ~100 m blocks, like tests/test_route.py.
const STEP = 0.0009;
const coord = (i, j) => [50.0 + i * STEP, 8.0 + j * STEP * 1.55];
function gridWays(n = 6) {
  const ways = [];
  const id = (i, j) => i * 100 + j;
  for (let i = 0; i < n; i++) for (let j = 0; j < n - 1; j++)
    ways.push({ nodes: [id(i, j), id(i, j + 1)], coords: [coord(i, j), coord(i, j + 1)], tags: { highway: "residential" } });
  for (let j = 0; j < n; j++) for (let i = 0; i < n - 1; i++)
    ways.push({ nodes: [id(i, j), id(i + 1, j)], coords: [coord(i, j), coord(i + 1, j)], tags: { highway: "residential" } });
  return ways;
}

test("classify follows the Python rules", () => {
  assert.equal(classify({ highway: "steps" })[1], "steps");
  assert.equal(classify({ highway: "footway", surface: "gravel" })[1], "rough surface");
  assert.equal(classify({ highway: "footway", incline: "12%" })[1], "steep");
  assert.deepEqual(classify({ highway: "residential" }), [true, null, 1.0]);
});

test("plans loops where every gap stays under the limit", () => {
  const graph = buildGraph(gridWays());
  const cells = [];
  for (let i = 0; i < 6; i++) for (let j = 0; j < 6; j++) if ((i + j) % 2 === 0) cells.push([i, j]);
  const seats = attachPoints(graph, cells.map(([i, j]) => ({ id: `s${i}${j}`, lat: coord(i, j)[0], lon: coord(i, j)[1], kind: "bench", source: "map" })));
  const plan = planWalks(graph, seats, [], coord(0, 0), [1000], 250);
  const r = plan.routes[0];
  assert.ok(r.found);
  assert.ok(r.length_m >= 850 && r.length_m <= 1300, `length ${r.length_m}`);
  assert.ok(r.max_gap_m <= 250, `gap ${r.max_gap_m}`);
  assert.deepEqual(r.path[0], r.path[r.path.length - 1]);
});

test("no seats means no walk, with a reason", () => {
  const plan = planWalks(buildGraph(gridWays()), [], [], coord(0, 0), [600]);
  assert.equal(plan.routes.length, 0);
  assert.equal(plan.no_route_reason, "it knows no places to sit here");
});

// Same OpenStreetMap data as the Python pipeline, when it is cached locally.
test("matches the Python result on cached Mainz data", { skip: !existsSync("data/cache/osm_mainz.json") }, () => {
  const city = JSON.parse(readFileSync("data/cities.json", "utf8")).mainz;
  const osm = parse(JSON.parse(readFileSync("data/cache/osm_mainz.json", "utf8")));
  const graph = buildGraph(osm.ways);
  const seats = attachPoints(graph, osm.seats);
  const plan = planWalks(graph, seats, [], [city.start.lat, city.start.lon], [600, 1000]);
  const python = JSON.parse(readFileSync("web/data/mainz.json", "utf8")).map_only;
  assert.equal(seats.length, python.seats_total);
  for (const r of plan.routes) {
    assert.ok(r.found, `no ${r.target_m} m loop`);
    assert.ok(r.max_gap_m <= 150, `gap ${r.max_gap_m}`);
  }
});
