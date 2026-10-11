// What the phone says during a walk. Pure functions: no DOM, no GPS, so they can be tested.

const EARTH_R = 6371000;
const rad = (d) => (d * Math.PI) / 180;

export function distanceM([lat1, lon1], [lat2, lon2]) {
  const h = Math.sin(rad(lat2 - lat1) / 2) ** 2 +
    Math.cos(rad(lat1)) * Math.cos(rad(lat2)) * Math.sin(rad(lon2 - lon1) / 2) ** 2;
  return 2 * EARTH_R * Math.asin(Math.sqrt(h));
}

// Point at distance `at` metres along the route.
export function pointAt(route, at) {
  const { path, cum_m: cum } = route;
  at = Math.min(Math.max(at, 0), cum[cum.length - 1]);
  for (let i = 1; i < cum.length; i++) {
    if (cum[i] >= at) {
      const f = (at - cum[i - 1]) / (cum[i] - cum[i - 1] || 1);
      return [path[i - 1][0] + (path[i][0] - path[i - 1][0]) * f, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * f];
    }
  }
  return path[path.length - 1];
}

// Where on the route is the walker? Searches only near the last known spot, so a loop that
// passes the same street twice does not make the walker jump ahead.
// Returns { at: metres along the route, off: metres away from the route }.
export function locate(route, point, lastAt = 0, back = 40, ahead = 250) {
  const { path, cum_m: cum } = route;
  const kx = Math.cos(rad(point[0])) * 111320, ky = 110540; // metres per degree, local flat approximation
  let best = { at: lastAt, off: Infinity };
  for (let i = 1; i < path.length; i++) {
    if (cum[i] < lastAt - back || cum[i - 1] > lastAt + ahead) continue;
    const ax = path[i - 1][1] * kx, ay = path[i - 1][0] * ky, bx = path[i][1] * kx, by = path[i][0] * ky;
    const px = point[1] * kx, py = point[0] * ky;
    const len2 = (bx - ax) ** 2 + (by - ay) ** 2 || 1;
    const t = Math.min(1, Math.max(0, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / len2));
    const off = Math.hypot(px - (ax + t * (bx - ax)), py - (ay + t * (by - ay)));
    if (off < best.off) best = { at: cum[i - 1] + t * (cum[i] - cum[i - 1]), off };
  }
  return best;
}

const SEAT_WORDS = {
  bench: "Bench",
  picnic_table: "Picnic table",
  shelter: "Shelter with a seat",
  tea_stall_bench: "Tea-stall bench",
  platform_or_ledge: "Place to sit",
  building_steps: "Steps to sit on",
  chair: "Chair",
  other: "Place to sit",
};
export const seatWord = (kind) => SEAT_WORDS[kind] || "Place to sit";

const roundTo10 = (m) => Math.max(10, Math.round(m / 10) * 10);

// Decide what to say now. `said` is a Set of cue keys already spoken; it is updated in place.
// Returns a list of sentences (often empty).
export function cuesAt(route, at, off, said, now = Date.now()) {
  const out = [];
  const once = (key, text) => { if (!said.has(key)) { said.add(key); out.push(text); } };
  const length = route.length_m;

  if (off > 35) {
    if (said.lastOffRoute === undefined || now - said.lastOffRoute > 30000) {
      said.lastOffRoute = now;
      out.push("You are off the route. Turn back to the path.");
    }
    return out;
  }

  if (!said.has("start")) {
    const first = route.seats.find((s) => s.at_m > 20);
    once("start", first
      ? `Walk started. ${seatWord(first.kind)} in ${roundTo10(first.at_m)} metres.`
      : "Walk started.");
  }

  route.seats.forEach((s, i) => {
    if (s.at_m < 20) return; // the bench you start from
    const d = s.at_m - at;
    if (d <= 15 && d >= -10) once(`seat-here-${i}`, `${seatWord(s.kind)} here. Rest if you like.`);
    else if (d > 40 && d <= 100) once(`seat-100-${i}`, `${seatWord(s.kind)} in ${roundTo10(d)} metres.`);
  });
  route.turns.forEach((t, i) => {
    const d = t.at_m - at;
    if (d > 0 && d <= 30) once(`turn-${i}`, `In ${roundTo10(d)} metres, turn ${t.dir}.`);
  });
  route.warnings.forEach((w, i) => {
    const d = w.at_m - at;
    if (d > 0 && d <= 40) once(`warn-${i}`, "Steps beside the path ahead. Stay on the route, it avoids them.");
  });
  (route.toilets || []).forEach((t, i) => {
    const d = t.at_m - at;
    if (d > 0 && d <= 40) once(`toilet-${i}`, "Toilet nearby.");
  });
  if (at >= length / 2) once("half", "Halfway. The way back is just as gentle.");
  if (at >= length - 15) once("end", "Walk complete. Well done.");
  return out;
}
