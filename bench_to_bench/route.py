"""Plan a loop that hops from seat to seat, never more than max_gap metres apart.

Everything here is plain, deterministic code. The language model never decides a route.
"""
import heapq
import random

from .geo import bearing_deg, distance_m, turn_angle


def shortest_paths(adj, sources, max_len):
    """Dijkstra by cost from several sources, stopping once walking length passes max_len.

    Returns {node: (length_m, cost, previous_node)} for every node reached.
    """
    best = {}
    heap = [(0.0, 0.0, s, None) for s in sources]
    while heap:
        cost, length, node, prev = heapq.heappop(heap)
        if node in best:
            continue
        best[node] = (length, cost, prev)
        for nxt, d, c in adj.get(node, ()):
            if nxt not in best and length + d <= max_len:
                heapq.heappush(heap, (cost + c, length + d, nxt, node))
    return best


def path_to(tree, node):
    """Walk the 'previous' links of a shortest_paths tree back to its source."""
    out = []
    while node is not None:
        out.append(node)
        node = tree[node][2]
    return out[::-1]


def seat_hops(graph, seat_nodes, max_gap):
    """For every seat node, the other seat nodes reachable within max_gap metres, with the path."""
    seat_set = set(seat_nodes)
    hops = {}
    for s in seat_nodes:
        tree = shortest_paths(graph["adj"], [s], max_gap)
        hops[s] = {t: (tree[t][0], path_to(tree, t)) for t in tree if t in seat_set and t != s}
    return hops


def _way_home(hops, start):
    """Seat-graph Dijkstra towards start: {seat: (metres to start, next seat on the way)}."""
    home = {start: (0.0, None)}
    heap = [(0.0, start)]
    while heap:
        d, n = heapq.heappop(heap)
        if d > home[n][0]:
            continue
        for m, (length, _) in hops[n].items():
            if m not in home or d + length < home[m][0]:
                home[m] = (d + length, n)
                heapq.heappush(heap, (d + length, m))
    return home


def find_loop(graph, seat_nodes, start, target_m, max_gap, tries=3000, seed=7, hops=None):
    """Search for a seat-to-seat loop from start (a seat node) of roughly target_m metres.

    Random restarts with a simple rule: hop to new seats, preferring ones further from home, until
    the walk out plus the shortest seat-to-seat way home is long enough; then go home. The best loop
    wins: closest to target_m, fewest repeated street segments.
    Returns None when no loop exists under these limits.
    """
    hops = hops or seat_hops(graph, seat_nodes, max_gap)
    if not hops.get(start):
        return None
    home = _way_home(hops, start)
    rng = random.Random(seed)
    best = None
    for _ in range(tries):
        stops, length, visited = [start], 0.0, {start}
        while True:
            cur = stops[-1]
            if len(stops) > 1 and length + home[cur][0] >= 0.85 * target_m:
                while cur != start:
                    nxt = home[cur][1]
                    length += hops[cur][nxt][0]
                    stops.append(nxt)
                    cur = nxt
                break
            options = [n for n in hops[cur] if n not in visited]
            if not options or length > 1.3 * target_m:
                stops = None
                break
            weights = [max(0.05, 1 + (home[n][0] - home[cur][0]) / 50) for n in options]
            nxt = rng.choices(options, weights)[0]
            stops.append(nxt)
            visited.add(nxt)
            length += hops[cur][nxt][0]
        if stops is None or length > 1.3 * target_m:
            continue
        nodes = [stops[0]]
        for a, b in zip(stops, stops[1:]):
            nodes += hops[a][b][1][1:]
        edges = list(zip(nodes, nodes[1:]))
        repeats = len(edges) - len({frozenset(e) for e in edges})
        score = abs(length - target_m) + 40 * repeats
        if best is None or score < best[0]:
            best = (score, stops, nodes, length)
    if best is None:
        return None
    _, stops, nodes, length = best
    return {"seat_stops": stops, "nodes": nodes, "length_m": length}


def describe(graph, loop, seats, toilets=(), min_turn_deg=40):
    """Lay out a loop for the phone: polyline, distances, seats, turns and warnings along the way."""
    coords, adj = graph["coords"], graph["adj"]
    nodes = loop["nodes"]
    path = [coords[n] for n in nodes]
    cum = [0.0]
    for a, b in zip(path, path[1:]):
        cum.append(cum[-1] + distance_m(a, b))

    seats_by_node = {}
    for s in seats:
        seats_by_node.setdefault(s["node"], []).append(s)
    on_route = []
    for i, n in enumerate(nodes[:-1]):
        for s in seats_by_node.get(n, ()):
            on_route.append({k: s[k] for k in ("id", "lat", "lon", "kind", "source") if k in s} | {
                "at_m": round(cum[i]), **({"photo": s["photo"]} if "photo" in s else {})})
    stops_at = sorted({x["at_m"] for x in on_route} | {0, round(cum[-1])})
    max_gap = max(b - a for a, b in zip(stops_at, stops_at[1:]))

    turns = []
    for i in range(1, len(nodes) - 1):
        if len(adj[nodes[i]]) <= 2:
            continue  # not a junction: the street just bends
        back = _point_at(path, cum, cum[i] - 12)
        ahead = _point_at(path, cum, cum[i] + 12)
        angle = turn_angle(bearing_deg(back, path[i]), bearing_deg(path[i], ahead))
        if abs(angle) >= min_turn_deg:
            turns.append({"at_m": round(cum[i]), "dir": "left" if angle < 0 else "right"})

    warnings = []
    for i, n in enumerate(nodes):
        if n in graph["steps_nodes"] and not any(abs(w["at_m"] - cum[i]) < 30 for w in warnings):
            warnings.append({"at_m": round(cum[i]), "kind": "steps"})

    near_toilets = [t | {"at_m": round(cum[min(range(len(path)), key=lambda i: distance_m(path[i], (t["lat"], t["lon"])))])}
                    for t in toilets if min(distance_m(p, (t["lat"], t["lon"])) for p in path) < 60]

    return {
        "length_m": round(cum[-1]),
        "max_gap_m": round(max_gap),
        "path": [[round(lat, 6), round(lon, 6)] for lat, lon in path],
        "cum_m": [round(c, 1) for c in cum],
        "seats": on_route,
        "turns": turns,
        "warnings": warnings,
        "toilets": near_toilets,
    }


def _point_at(path, cum, at):
    """Point at distance `at` along the polyline (clamped to its ends)."""
    at = min(max(at, 0), cum[-1])
    for i in range(1, len(cum)):
        if cum[i] >= at:
            span = cum[i] - cum[i - 1] or 1
            f = (at - cum[i - 1]) / span
            (a1, o1), (a2, o2) = path[i - 1], path[i]
            return (a1 + (a2 - a1) * f, o1 + (o2 - o1) * f)
    return path[-1]


def coverage(graph, seat_nodes, radius_m=75):
    """Share of walkable street length that is within radius_m walking distance of a seat (0..1)."""
    reach = shortest_paths(graph["adj"], list(seat_nodes), radius_m) if seat_nodes else {}
    total = covered = 0.0
    seen = set()
    for a, nbrs in graph["adj"].items():
        for b, d, _ in nbrs:
            key = frozenset((a, b))
            if key in seen:
                continue
            seen.add(key)
            total += d
            # the part of this segment within radius_m of a seat, reached from either end
            from_a = max(0.0, radius_m - reach[a][0]) if a in reach else 0.0
            from_b = max(0.0, radius_m - reach[b][0]) if b in reach else 0.0
            covered += min(d, from_a + from_b)
    return covered / total if total else 0.0
