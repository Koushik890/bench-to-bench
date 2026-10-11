"""Turn OSM streets into a graph a person with knee pain can walk: no steps, no rough ground."""
from .geo import GridIndex, distance_m

# Streets people may not walk on at all.
NOT_WALKABLE = {
    "motorway", "motorway_link", "trunk", "trunk_link", "construction", "proposed",
    "raceway", "bus_guideway", "escape", "abandoned", "platform", "corridor", "elevator",
}
# Ground that is hard on painful knees.
ROUGH_SURFACES = {
    "unpaved", "gravel", "dirt", "earth", "ground", "grass", "sand", "mud", "rock",
    "pebblestone", "cobblestone", "unhewn_cobblestone", "woodchips", "stepping_stones",
}
# Busy roads stay allowed (they usually have pavements) but cost more, so quiet streets win.
BUSY_ROADS = {"primary", "primary_link", "secondary", "secondary_link"}


def classify(tags):
    """Decide whether a way can be part of a route.

    Returns (allowed, reason, cost_factor). reason explains a refusal.
    """
    hw = tags.get("highway", "")
    if hw == "steps":
        return False, "steps", None
    if hw in NOT_WALKABLE:
        return False, "not walkable", None
    if tags.get("foot") in ("no", "private") or (tags.get("access") in ("no", "private") and tags.get("foot") not in ("yes", "designated", "permissive")):
        return False, "no access", None
    if tags.get("surface") in ROUGH_SURFACES:
        return False, "rough surface", None
    if tags.get("smoothness") in ("bad", "very_bad", "horrible", "very_horrible", "impassable"):
        return False, "rough surface", None
    incline = tags.get("incline", "").rstrip("%")
    try:
        if abs(float(incline)) > 6:
            return False, "steep", None
    except ValueError:
        pass
    return True, None, 1.3 if hw in BUSY_ROADS else 1.0


def build(ways):
    """Build the walking graph.

    Returns a dict with:
      coords: node_id -> (lat, lon)
      adj:    node_id -> list of (neighbour, length_m, cost)
      steps_nodes: node ids that touch a flight of steps (for "steps ahead" warnings)
      refused: {reason: metres} of street length left out, for reporting
    """
    coords, adj, steps_nodes, refused = {}, {}, set(), {}
    for way in ways:
        allowed, reason, factor = classify(way["tags"])
        pairs = list(zip(way["nodes"], way["coords"]))
        if not allowed:
            length = sum(distance_m(a[1], b[1]) for a, b in zip(pairs, pairs[1:]))
            refused[reason] = refused.get(reason, 0) + length
            if reason == "steps":
                steps_nodes.update(n for n, _ in pairs)
            continue
        for (n1, c1), (n2, c2) in zip(pairs, pairs[1:]):
            d = distance_m(c1, c2)
            coords[n1], coords[n2] = c1, c2
            adj.setdefault(n1, []).append((n2, d, d * factor))
            adj.setdefault(n2, []).append((n1, d, d * factor))
    return {"coords": coords, "adj": adj, "steps_nodes": steps_nodes & set(coords), "refused": refused}


def attach_points(graph, points, max_snap_m=30):
    """Snap points (seats, toilets) to their nearest graph node.

    Returns (attached, dropped): attached items gain a 'node' key; dropped ones were too far from any street.
    """
    index = GridIndex(graph["coords"])
    attached, dropped = [], []
    for p in points:
        node, d = index.nearest((p["lat"], p["lon"]), max_snap_m)
        if node is None:
            dropped.append(p)
        else:
            attached.append({**p, "node": node, "snap_m": round(d, 1)})
    return attached, dropped
