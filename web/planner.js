// Plan seat-to-seat walks around any point, in the browser.
// Same rules as the Python pipeline (bench_to_bench/walkgraph.py and route.py): no steps,
// no rough ground, every stretch between seats at most maxGap metres. Plain code; no model involved.
import { distanceM } from "./cues.js";

const OVERPASS_URLS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
];
const SEAT_TAGS = [["amenity", "bench"], ["leisure", "picnic_table"], ["amenity", "shelter"]];
const NOT_WALKABLE = new Set(["motorway", "motorway_link", "trunk", "trunk_link", "construction", "proposed",
  "raceway", "bus_guideway", "escape", "abandoned", "platform", "corridor", "elevator"]);
const ROUGH_SURFACES = new Set(["unpaved", "gravel", "dirt", "earth", "ground", "grass", "sand", "mud", "rock",
  "pebblestone", "cobblestone", "unhewn_cobblestone", "woodchips", "stepping_stones"]);
const BUSY_ROADS = new Set(["primary", "primary_link", "secondary", "secondary_link"]);

// ---------- map data ----------

export function bboxAround(lat, lon, radiusM) {
  const dLat = radiusM / 110540, dLon = radiusM / (111320 * Math.cos((lat * Math.PI) / 180));
  return [lat - dLat, lon - dLon, lat + dLat, lon + dLon];
}

export function buildQuery([s, w, n, e]) {
  const b = `(${s},${w},${n},${e})`;
  const seats = SEAT_TAGS.map(([k, v]) => `node["${k}"="${v}"]${b};`).join("");
  return `[out:json][timeout:60];way["highway"]${b};out body geom;(${seats}node["amenity"="toilets"]${b};);out body;`;
}

export async function fetchOsm(bbox, fetchFn = fetch, retryDelayMs = 3000) {
  const errors = [];
  // The main server often answers 504 when busy; it usually works a few seconds later.
  const attempts = [OVERPASS_URLS[0], OVERPASS_URLS[0], ...OVERPASS_URLS.slice(1)];
  for (const [i, url] of attempts.entries()) {
    if (i === 1) await new Promise((r) => setTimeout(r, retryDelayMs));
    try {
      const resp = await fetchFn(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: "data=" + encodeURIComponent(buildQuery(bbox)),
      });
      if (resp.ok) return await resp.json();
      errors.push(`${url}: HTTP ${resp.status}`);
    } catch (err) {
      errors.push(`${url}: ${err.message}`);
    }
  }
  console.warn("Overpass failed:", errors);
  throw new Error("The map server is busy right now. Try again in a minute.");
}

export function parse(raw) {
  const ways = [], seats = [], toilets = [];
  for (const el of raw.elements || []) {
    const tags = el.tags || {};
    if (el.type === "way" && el.geometry && tags.highway) {
      ways.push({ id: el.id, nodes: el.nodes, coords: el.geometry.map((g) => [g.lat, g.lon]), tags });
    } else if (el.type === "node") {
      if (tags.amenity === "toilets") toilets.push({ id: `osm/${el.id}`, lat: el.lat, lon: el.lon });
      if (SEAT_TAGS.some(([k, v]) => tags[k] === v)) {
        const kind = tags.amenity === "bench" ? "bench" : tags.leisure || tags.amenity;
        seats.push({ id: `osm/${el.id}`, lat: el.lat, lon: el.lon, kind, source: "map" });
      }
    }
  }
  return { ways, seats, toilets };
}

// ---------- walking graph ----------

export function classify(tags) {
  const hw = tags.highway || "";
  if (hw === "steps") return [false, "steps", null];
  if (NOT_WALKABLE.has(hw)) return [false, "not walkable", null];
  const footOk = ["yes", "designated", "permissive"].includes(tags.foot);
  if (["no", "private"].includes(tags.foot) || (["no", "private"].includes(tags.access) && !footOk)) return [false, "no access", null];
  if (ROUGH_SURFACES.has(tags.surface)) return [false, "rough surface", null];
  if (["bad", "very_bad", "horrible", "very_horrible", "impassable"].includes(tags.smoothness)) return [false, "rough surface", null];
  const incline = parseFloat(String(tags.incline || "").replace("%", ""));
  if (!Number.isNaN(incline) && Math.abs(incline) > 6) return [false, "steep", null];
  return [true, null, BUSY_ROADS.has(hw) ? 1.3 : 1.0];
}

export function buildGraph(ways) {
  const coords = new Map(), adj = new Map(), stepsNodes = new Set();
  const link = (a, b, d, c) => { if (!adj.has(a)) adj.set(a, []); adj.get(a).push([b, d, c]); };
  for (const way of ways) {
    const [allowed, reason, factor] = classify(way.tags);
    if (!allowed) {
      if (reason === "steps") way.nodes.forEach((n) => stepsNodes.add(n));
      continue;
    }
    for (let i = 1; i < way.nodes.length; i++) {
      const [n1, n2, c1, c2] = [way.nodes[i - 1], way.nodes[i], way.coords[i - 1], way.coords[i]];
      const d = distanceM(c1, c2);
      coords.set(n1, c1); coords.set(n2, c2);
      link(n1, n2, d, d * factor); link(n2, n1, d, d * factor);
    }
  }
  for (const n of [...stepsNodes]) if (!coords.has(n)) stepsNodes.delete(n);
  return { coords, adj, stepsNodes };
}

// Snap points to their nearest graph node within maxSnapM (a coarse grid keeps it fast).
export function attachPoints(graph, points, maxSnapM = 30) {
  const cell = 0.002, grid = new Map();
  const key = (lat, lon) => `${Math.floor(lat / cell)},${Math.floor(lon / cell)}`;
  for (const [n, c] of graph.coords) {
    const k = key(c[0], c[1]);
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push([n, c]);
  }
  const attached = [];
  for (const p of points) {
    const ci = Math.floor(p.lat / cell), cj = Math.floor(p.lon / cell);
    let best = null, bestD = Infinity;
    for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
      for (const [n, c] of grid.get(`${ci + di},${cj + dj}`) || []) {
        const d = distanceM([p.lat, p.lon], c);
        if (d < bestD) { best = n; bestD = d; }
      }
    }
    if (best !== null && bestD <= maxSnapM) attached.push({ ...p, node: best });
  }
  return attached;
}

// ---------- routes ----------

class Heap {
  constructor() { this.a = []; }
  push(x) { const a = this.a; a.push(x); let i = a.length - 1;
    while (i > 0) { const p = (i - 1) >> 1; if (a[p][0] <= a[i][0]) break; [a[p], a[i]] = [a[i], a[p]]; i = p; } }
  pop() { const a = this.a, top = a[0], last = a.pop();
    if (a.length) { a[0] = last; let i = 0;
      for (;;) { const l = 2 * i + 1, r = l + 1; let m = i;
        if (l < a.length && a[l][0] < a[m][0]) m = l;
        if (r < a.length && a[r][0] < a[m][0]) m = r;
        if (m === i) break; [a[m], a[i]] = [a[i], a[m]]; i = m; } }
    return top; }
  get size() { return this.a.length; }
}

// Dijkstra by cost from sources, stopping once walking length passes maxLen: node -> [length, cost, prev].
export function shortestPaths(adj, sources, maxLen) {
  const best = new Map(), heap = new Heap();
  for (const s of sources) heap.push([0, 0, s, null]);
  while (heap.size) {
    const [cost, length, node, prev] = heap.pop();
    if (best.has(node)) continue;
    best.set(node, [length, cost, prev]);
    for (const [nxt, d, c] of adj.get(node) || []) {
      if (!best.has(nxt) && length + d <= maxLen) heap.push([cost + c, length + d, nxt, node]);
    }
  }
  return best;
}

function pathTo(tree, node) {
  const out = [];
  while (node !== null) { out.push(node); node = tree.get(node)[2]; }
  return out.reverse();
}

export function seatHops(graph, seatNodes, maxGap) {
  const seatSet = new Set(seatNodes), hops = new Map();
  for (const s of seatNodes) {
    const tree = shortestPaths(graph.adj, [s], maxGap), m = new Map();
    for (const [t, [len]] of tree) if (seatSet.has(t) && t !== s) m.set(t, [len, pathTo(tree, t)]);
    hops.set(s, m);
  }
  return hops;
}

function wayHome(hops, start) {
  const home = new Map([[start, [0, null]]]), heap = new Heap();
  heap.push([0, start]);
  while (heap.size) {
    const [d, n] = heap.pop();
    if (d > home.get(n)[0]) continue;
    for (const [m, [len]] of hops.get(n)) {
      if (!home.has(m) || d + len < home.get(m)[0]) { home.set(m, [d + len, n]); heap.push([d + len, m]); }
    }
  }
  return home;
}

function mulberry32(seed) {
  return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// Seat-to-seat loop from start of roughly targetM metres, or null. Same rule as route.find_loop.
export function findLoop(hops, start, targetM, tries = 1500, seed = 7) {
  if (!hops.get(start)?.size) return null;
  const home = wayHome(hops, start), rand = mulberry32(seed);
  let best = null;
  for (let t = 0; t < tries; t++) {
    let stops = [start], length = 0;
    const visited = new Set([start]);
    for (;;) {
      let cur = stops[stops.length - 1];
      if (stops.length > 1 && length + home.get(cur)[0] >= 0.85 * targetM) {
        while (cur !== start) { const nxt = home.get(cur)[1]; length += hops.get(cur).get(nxt)[0]; stops.push(nxt); cur = nxt; }
        break;
      }
      const options = [...hops.get(cur).keys()].filter((n) => !visited.has(n));
      if (!options.length || length > 1.3 * targetM) { stops = null; break; }
      const weights = options.map((n) => Math.max(0.05, 1 + (home.get(n)[0] - home.get(cur)[0]) / 50));
      let r = rand() * weights.reduce((a, b) => a + b, 0), i = 0;
      while ((r -= weights[i]) > 0 && i < options.length - 1) i++;
      const nxt = options[i];
      stops.push(nxt); visited.add(nxt); length += hops.get(cur).get(nxt)[0];
    }
    if (!stops || length > 1.3 * targetM) continue;
    let nodes = [stops[0]];
    for (let i = 1; i < stops.length; i++) nodes = nodes.concat(hops.get(stops[i - 1]).get(stops[i])[1].slice(1));
    const edges = new Set(), all = nodes.length - 1;
    for (let i = 1; i < nodes.length; i++) edges.add([nodes[i - 1], nodes[i]].sort().join("|"));
    const score = Math.abs(length - targetM) + 40 * (all - edges.size);
    if (!best || score < best.score) best = { score, nodes, length };
  }
  return best && { nodes: best.nodes, length_m: best.length };
}

const bearing = ([lat1, lon1], [lat2, lon2]) => {
  const r = Math.PI / 180, y = Math.sin((lon2 - lon1) * r) * Math.cos(lat2 * r);
  const x = Math.cos(lat1 * r) * Math.sin(lat2 * r) - Math.sin(lat1 * r) * Math.cos(lat2 * r) * Math.cos((lon2 - lon1) * r);
  return ((Math.atan2(y, x) / r) + 360) % 360;
};

function pointAlong(path, cum, at) {
  at = Math.min(Math.max(at, 0), cum[cum.length - 1]);
  for (let i = 1; i < cum.length; i++) {
    if (cum[i] >= at) { const f = (at - cum[i - 1]) / (cum[i] - cum[i - 1] || 1);
      return [path[i - 1][0] + (path[i][0] - path[i - 1][0]) * f, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * f]; }
  }
  return path[path.length - 1];
}

// Lay out a loop for the phone: same shape as route.describe in Python.
export function describe(graph, loop, seats, toilets = []) {
  const { coords, adj, stepsNodes } = graph, nodes = loop.nodes;
  const path = nodes.map((n) => coords.get(n)), cum = [0];
  for (let i = 1; i < path.length; i++) cum.push(cum[i - 1] + distanceM(path[i - 1], path[i]));
  const byNode = new Map();
  for (const s of seats) { if (!byNode.has(s.node)) byNode.set(s.node, []); byNode.get(s.node).push(s); }
  const onRoute = [];
  nodes.slice(0, -1).forEach((n, i) => (byNode.get(n) || []).forEach((s) =>
    onRoute.push({ id: s.id, lat: s.lat, lon: s.lon, kind: s.kind, source: s.source, at_m: Math.round(cum[i]), ...(s.photo ? { photo: s.photo } : {}) })));
  const stops = [...new Set([0, Math.round(cum[cum.length - 1]), ...onRoute.map((s) => s.at_m)])].sort((a, b) => a - b);
  let maxGap = 0;
  for (let i = 1; i < stops.length; i++) maxGap = Math.max(maxGap, stops[i] - stops[i - 1]);
  const turns = [];
  for (let i = 1; i < nodes.length - 1; i++) {
    if ((adj.get(nodes[i]) || []).length <= 2) continue;
    const angle = ((bearing(path[i], pointAlong(path, cum, cum[i] + 12)) - bearing(pointAlong(path, cum, cum[i] - 12), path[i]) + 540) % 360) - 180;
    if (Math.abs(angle) >= 150) turns.push({ at_m: Math.round(cum[i]), dir: "around" });
    else if (Math.abs(angle) >= 40) turns.push({ at_m: Math.round(cum[i]), dir: angle < 0 ? "left" : "right" });
  }
  const warnings = [];
  nodes.forEach((n, i) => {
    if (stepsNodes.has(n) && !warnings.some((w) => Math.abs(w.at_m - cum[i]) < 30)) warnings.push({ at_m: Math.round(cum[i]), kind: "steps" });
  });
  const near = toilets.map((t) => {
    let bi = 0, bd = Infinity;
    path.forEach((p, i) => { const d = distanceM(p, [t.lat, t.lon]); if (d < bd) { bd = d; bi = i; } });
    return bd < 60 ? { ...t, at_m: Math.round(cum[bi]) } : null;
  }).filter(Boolean);
  return {
    length_m: Math.round(cum[cum.length - 1]), max_gap_m: Math.round(maxGap),
    path: path.map(([a, b]) => [+a.toFixed(6), +b.toFixed(6)]), cum_m: cum.map((c) => +c.toFixed(1)),
    seats: onRoute, turns, warnings, toilets: near,
  };
}

// Walks of each length from the seat near `point` that allows the most of them (same as build_city.plan).
export function planWalks(graph, seats, toilets, point, lengths, maxGap = 150) {
  const seatNodes = [...new Set(seats.map((s) => s.node))];
  const result = { seats_total: seats.length, routes: [] };
  const hops = seatHops(graph, seatNodes, maxGap);
  const candidates = seatNodes.filter((n) => hops.get(n).size)
    .sort((a, b) => distanceM(graph.coords.get(a), point) - distanceM(graph.coords.get(b), point));
  if (!candidates.length) {
    result.no_route_reason = seatNodes.length ? `no two seats are within ${maxGap} m walking distance of each other`
      : "it knows no places to sit here";
    return result;
  }
  let best = null;
  for (const node of candidates.slice(0, 15)) {
    const loops = lengths.map((t) => findLoop(hops, node, t));
    const found = loops.filter(Boolean).length;
    if (!best || found > best.found) best = { found, node, loops };
    if (found === lengths.length) break;
  }
  result.start_seat_from_start_m = Math.round(distanceM(graph.coords.get(best.node), point));
  lengths.forEach((target, i) => {
    const loop = best.loops[i];
    result.routes.push(loop ? { target_m: target, found: true, ...describe(graph, loop, seats, toilets) } : { target_m: target, found: false });
  });
  return result;
}
