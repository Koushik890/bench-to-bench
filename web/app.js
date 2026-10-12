import { cuesAt, distanceM, locate, pointAt, seatWord } from "./cues.js";
import { attachPoints, bboxAround, buildGraph, fetchOsm, parse, planWalks } from "./planner.js";

const state = { source: "with_gemma", target: 1000, data: null, route: null };
const $ = (sel) => document.querySelector(sel);
const NEAR_ME_RADIUS_M = 900;
const NEAR_ME_LENGTHS = [250, 600, 1000, 1500];

// ---------- map ----------
const map = L.map("map", { zoomControl: true });
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
const layer = L.layerGroup().addTo(map);
map.setView([30, 40], 2); // until your location is known

function currentPosition() {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) reject(new Error("This browser cannot share its location."));
    else navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 });
  });
}

// Plan walks around where the phone is: map benches, plus any seats Gemma found in photos of this area.
async function loadNearMe() {
  $("#summary").innerHTML = `<p class="big">Finding places to sit near you…</p>`;
  const pos = await currentPosition();
  const point = [pos.coords.latitude, pos.coords.longitude];
  const bbox = bboxAround(...point, NEAR_ME_RADIUS_M);
  const osmData = parse(await fetchOsm(bbox));
  const graph = buildGraph(osmData.ways);
  const mapSeats = attachPoints(graph, osmData.seats);
  const toilets = attachPoints(graph, osmData.toilets, 60);
  let gemmaSeats = [];
  try {
    const all = await (await fetch("../data/gemma_seats_kolkata.json")).json();
    const [s, w, n, e] = bbox;
    gemmaSeats = attachPoints(graph, all.filter((p) => p.lat >= s && p.lat <= n && p.lon >= w && p.lon <= e));
  } catch { /* no photo seats published for this area */ }
  const data = {
    name: "Near you",
    start: { name: "You are here", lat: point[0], lon: point[1] },
    max_gap_m: 150,
    map_only: planWalks(graph, mapSeats, toilets, point, NEAR_ME_LENGTHS),
  };
  if (gemmaSeats.length) data.with_gemma = planWalks(graph, mapSeats.concat(gemmaSeats), toilets, point, NEAR_ME_LENGTHS);
  return data;
}

function variant(data) {
  return data[state.source] || data.map_only;
}

function pickRoute(v) {
  return v.routes.find((r) => r.target_m === state.target && r.found) || null;
}

function setPressed(selector, attr, value) {
  document.querySelectorAll(selector).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset[attr] === String(value))));
}

async function render() {
  let data;
  try {
    data = state.data ||= await loadNearMe();
  } catch (err) {
    showProblem(err);
    return;
  }
  if (!data.with_gemma) state.source = "map_only";
  $("#sourceRow").hidden = !data.with_gemma;
  setPressed("[data-source]", "source", state.source);

  const v = variant(data);
  const lengths = v.routes.length ? v.routes : data.map_only.routes;
  $("#lengthRow").innerHTML = lengths.map((r) =>
    `<button class="chip" data-target="${r.target_m}" ${r.found ? "" : "disabled"}>${r.target_m >= 1000 ? r.target_m / 1000 + " km" : r.target_m + " m"}</button>`).join("");
  if (!pickRoute(v)) {
    const firstFound = v.routes.find((r) => r.found);
    if (firstFound) state.target = firstFound.target_m;
  }
  setPressed("[data-target]", "target", state.target);

  state.route = pickRoute(v);
  layer.clearLayers();
  const startLatLng = [data.start.lat, data.start.lon];
  L.circleMarker(startLatLng, { radius: 7, color: "#111", fillColor: "#fff", fillOpacity: 1, weight: 3 })
    .bindPopup(`Start: ${data.start.name}`).addTo(layer);

  if (state.route) {
    const line = L.polyline(state.route.path, { color: "#15803d", weight: 6, opacity: 0.85 }).addTo(layer);
    for (const s of state.route.seats) addSeat(s);
    for (const w of state.route.warnings) {
      L.circleMarker(pointAt(state.route, w.at_m), { radius: 6, color: "#b91c1c", fillOpacity: 0.9 })
        .bindPopup("Steps beside the route (the route avoids them)").addTo(layer);
    }
    map.fitBounds(line.getBounds(), { padding: [20, 20] });
  } else {
    map.setView(startLatLng, 15);
  }
  renderSummary(data, v);
  $("#startWalk").disabled = $("#practiceWalk").disabled = !state.route;
}

function showProblem(err) {
  const denied = err && err.code === 1;
  $("#summary").innerHTML = `<p class="big bad">${denied ? "Location is off." : "Could not plan walks here."}</p>` +
    `<p>${denied ? "Allow location for this page to find walks near you." : err.message || "Please try again."}</p>` +
    `<button class="chip" id="retry">Try again</button>`;
  $("#lengthRow").innerHTML = "";
  $("#sourceRow").hidden = true;
  $("#startWalk").disabled = $("#practiceWalk").disabled = true;
  state.data = null;
}

function addSeat(s) {
  const gemma = s.source === "gemma";
  const popup = gemma
    ? `<b>${seatWord(s.kind)}</b> seen by Gemma in a street photo.<br>` +
      `<a href="https://www.mapillary.com/app/?pKey=${s.photo}" target="_blank" rel="noopener">Open photo on Mapillary</a>`
    : `<b>${seatWord(s.kind)}</b> from OpenStreetMap`;
  L.circleMarker([s.lat, s.lon], {
    radius: 7, color: gemma ? "#c2410c" : "#1d4ed8", fillColor: gemma ? "#fb923c" : "#60a5fa", fillOpacity: 0.95, weight: 2,
  }).bindPopup(popup).addTo(layer);
}

function renderSummary(data, v) {
  const r = state.route;
  const unique = r ? [...new Map(r.seats.map((s) => [s.id, s])).values()] : [];
  const gemmaCount = unique.filter((s) => s.source === "gemma").length;
  let html = "";
  if (r) {
    const shape = r.turns.some((t) => t.dir === "around") ? "there-and-back walk" : "loop";
    html += `<p class="big">${(r.length_m / 1000).toFixed(2)} km ${shape} · never more than ${r.max_gap_m} m without a seat</p><ul>`;
    html += `<li>${unique.length} places to sit on the way` +
      (gemmaCount ? ` (<span class="legend-dot" style="background:#fb923c"></span>${gemmaCount} found by Gemma in photos)` : "") + "</li>";
    html += `<li>No steps, no gravel or cobblestones</li>`;
    html += `<li>${r.turns.length} turns, spoken 30 m ahead</li></ul>`;
  } else {
    html += `<p class="big bad">No safe walk possible here.</p>`;
    html += `<p>${v.no_route_reason ? "The map is no help: " + v.no_route_reason + "." : "No loop keeps every stretch under " + data.max_gap_m + " m between seats."}</p>`;
  }
  const coverage = v.coverage_75m === undefined ? "" : `, ${Math.round(v.coverage_75m * 100)}% of streets within 75 m of one`;
  const startNote = r && v.start_seat_from_start_m > 30 ? `. The walk starts at a seat ${v.start_seat_from_start_m} m from you` : "";
  html += `<ul><li>${data.name}: ${v.seats_total} known places to sit${coverage}${startNote}</li></ul>`;
  $("#summary").innerHTML = html;
}

// ---------- walking ----------
let walk = null;

function speak(text) {
  $("#walkLast").textContent = text;
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = navigator.language || "en";
  u.rate = 0.95;
  speechSynthesis.speak(u);
}

async function startWalk(practice) {
  const route = state.route;
  if (!route) return;
  speechSynthesis?.cancel();
  speak(""); // unlocks speech on phones: it must start inside a tap
  $("#walk").hidden = false;
  walk = { route, at: 0, said: new Set(), practice, watchId: null, timer: null, lock: null };
  try { walk.lock = await navigator.wakeLock?.request("screen"); } catch { /* screen may still dim */ }

  const onPosition = (point) => {
    const pos = locate(route, point, walk.at);
    if (pos.off <= 35) walk.at = Math.max(walk.at, pos.at);
    $("#walkStatus").textContent = `${Math.round(walk.at)} m of ${route.length_m} m`;
    for (const text of cuesAt(route, walk.at, pos.off, walk.said)) speak(text);
    if (walk.said.has("end")) setTimeout(stopWalk, 4000);
  };

  if (practice) {
    // Pretend to walk at 1.2 m/s, eight times faster than real time, along the route.
    let at = 0;
    walk.timer = setInterval(() => {
      at += 1.2 * 8;
      onPosition(pointAt(route, at));
    }, 1000);
  } else if ("geolocation" in navigator) {
    walk.watchId = navigator.geolocation.watchPosition(
      (p) => onPosition([p.coords.latitude, p.coords.longitude]),
      () => speak("I cannot get your location. Please allow location for this page."),
      { enableHighAccuracy: true, maximumAge: 2000 },
    );
  }
}

function stopWalk() {
  if (!walk) return;
  clearInterval(walk.timer);
  if (walk.watchId !== null) navigator.geolocation.clearWatch(walk.watchId);
  walk.lock?.release?.();
  walk = null;
  $("#walk").hidden = true;
}

// ---------- events ----------
document.addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  if (b.id === "retry") render();
  else if (b.dataset.source) { state.source = b.dataset.source; render(); }
  else if (b.dataset.target) { state.target = Number(b.dataset.target); render(); }
});
$("#startWalk").addEventListener("click", () => startWalk(false));
$("#practiceWalk").addEventListener("click", () => startWalk(true));
$("#walk").addEventListener("dblclick", stopWalk);
document.addEventListener("visibilitychange", async () => {
  if (walk && document.visibilityState === "visible") {
    try { walk.lock = await navigator.wakeLock?.request("screen"); } catch { /* ignore */ }
  }
});

// Exposed for tests and the demo recording.
window.benchToBench = { state, render, distanceM };
render();
