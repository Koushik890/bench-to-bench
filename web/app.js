import { cuesAt, distanceM, locate, pointAt, seatWord } from "./cues.js";

const state = { city: "mainz", source: "map_only", target: 1000, data: {}, route: null };
const $ = (sel) => document.querySelector(sel);

// ---------- map ----------
const map = L.map("map", { zoomControl: true });
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
const layer = L.layerGroup().addTo(map);

async function loadCity(city) {
  if (!state.data[city]) state.data[city] = await (await fetch(`data/${city}.json`)).json();
  return state.data[city];
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
  const data = await loadCity(state.city);
  if (!data.with_gemma) state.source = "map_only";
  $("#sourceRow").hidden = !data.with_gemma;
  setPressed("[data-city]", "city", state.city);
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
  const gemmaCount = r ? r.seats.filter((s) => s.source === "gemma").length : 0;
  let html = "";
  if (r) {
    html += `<p class="big">${(r.length_m / 1000).toFixed(2)} km loop · never more than ${r.max_gap_m} m without a seat</p><ul>`;
    html += `<li>${r.seats.length} places to sit on the way` +
      (gemmaCount ? ` (<span class="legend-dot" style="background:#fb923c"></span>${gemmaCount} found by Gemma in photos)` : "") + "</li>";
    html += `<li>No steps, no gravel or cobblestones</li>`;
    html += `<li>${r.turns.length} turns, spoken 30 m ahead</li></ul>`;
  } else {
    html += `<p class="big bad">No safe walk possible here.</p>`;
    html += `<p>${v.no_route_reason ? "The map knows too few places to sit: " + v.no_route_reason + "." : "No loop keeps every stretch under " + data.max_gap_m + " m between seats."}</p>`;
  }
  html += `<ul><li>${data.name}: ${v.seats_total} known places to sit, ${Math.round(v.coverage_75m * 100)}% of streets within 75 m of one</li></ul>`;
  $("#summary").innerHTML = html;
}

// ---------- walking ----------
let walk = null;

function speak(text) {
  $("#walkLast").textContent = text;
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = state.city === "kolkata" ? "en-IN" : "en-GB";
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
  if (b.dataset.city) { state.city = b.dataset.city; state.source = b.dataset.city === "kolkata" ? "with_gemma" : "map_only"; render(); }
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
