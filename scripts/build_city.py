"""Build the route file the phone app loads: web/data/<city>.json.

Usage:
  python scripts/build_city.py mainz
  python scripts/build_city.py kolkata --gemma-seats data/gemma_seats_kolkata.json

Seats come from OpenStreetMap, plus (optionally) places to sit that Gemma found in street photos.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench_to_bench import osm, route, walkgraph  # noqa: E402
from bench_to_bench.geo import distance_m  # noqa: E402

LENGTHS_M = [600, 1000, 1500]  # cities.json may set its own "lengths_m"
MAX_GAP_M = 150
START_CANDIDATES = 25


def plan(graph, seats, toilets, start, lengths=LENGTHS_M, max_gap=MAX_GAP_M):
    """Routes for each target length plus coverage numbers for one set of seats.

    The loop starts at a seat near the chosen start point: of the closest seats, the first one
    from which loops of the most target lengths exist.
    """
    seat_nodes = sorted({s["node"] for s in seats})
    result = {
        "seats_total": len(seats),
        "coverage_75m": round(route.coverage(graph, seat_nodes, 75), 3),
        "routes": [],
    }
    hops = route.seat_hops(graph, seat_nodes, max_gap)
    point = (start["lat"], start["lon"])
    candidates = sorted((n for n in seat_nodes if hops.get(n)), key=lambda n: distance_m(graph["coords"][n], point))
    if not candidates:
        result["no_route_reason"] = ("it knows no places to sit here" if not seat_nodes else
                                     f"no two seats are within {max_gap} m walking distance of each other")
        return result
    best = None
    for node in candidates[:START_CANDIDATES]:
        loops = [route.find_loop(graph, seat_nodes, node, t, max_gap, hops=hops) for t in lengths]
        found = sum(1 for lp in loops if lp)
        if best is None or found > best[0]:
            best = (found, node, loops)
        if found == len(lengths):
            break
    _, node, loops = best
    result["start_seat_from_start_m"] = round(distance_m(graph["coords"][node], point))
    for target, loop in zip(lengths, loops):
        if loop is None:
            result["routes"].append({"target_m": target, "found": False})
        else:
            result["routes"].append({"target_m": target, "found": True, **route.describe(graph, loop, seats, toilets)})
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("--gemma-seats", help="JSON list of seats found by Gemma in photos")
    args = ap.parse_args()

    city = json.loads((ROOT / "data/cities.json").read_text(encoding="utf-8"))[args.city]
    lengths = city.get("lengths_m", LENGTHS_M)
    data = osm.load_city(city["bbox"], ROOT / f"data/cache/osm_{args.city}.json")
    graph = walkgraph.build(data["ways"])
    map_seats, dropped = walkgraph.attach_points(graph, data["seats"])
    toilets, _ = walkgraph.attach_points(graph, data["toilets"], 60)

    out = {
        "city": args.city,
        "name": city["name"],
        "start": city["start"],
        "max_gap_m": MAX_GAP_M,
        "streets": {
            "walkable_km": round(sum(d for nbrs in graph["adj"].values() for _, d, _ in nbrs) / 2000, 1),
            "left_out_km": {k: round(v / 1000, 2) for k, v in sorted(graph["refused"].items())},
        },
        "map_only": plan(graph, map_seats, toilets, city["start"], lengths),
        "seats_not_on_a_street": len(dropped),
    }
    if args.gemma_seats:
        gemma_seats, gemma_dropped = walkgraph.attach_points(
            graph, json.loads(Path(args.gemma_seats).read_text(encoding="utf-8")))
        out["with_gemma"] = plan(graph, map_seats + gemma_seats, toilets, city["start"], lengths)
        out["gemma_seats_added"] = len(gemma_seats)
        out["gemma_seats_not_on_a_street"] = len(gemma_dropped)

    dest = ROOT / f"web/data/{args.city}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")

    for variant in ("map_only", "with_gemma"):
        if variant not in out:
            continue
        v = out[variant]
        print(f"{args.city} {variant}: {v['seats_total']} seats, {v['coverage_75m']:.0%} of streets within 75 m of a seat")
        if "no_route_reason" in v:
            print("  no route:", v["no_route_reason"])
        for r in v["routes"]:
            if r["found"]:
                print(f"  target {r['target_m']} m -> {r['length_m']} m, longest stretch without a seat {r['max_gap_m']} m, "
                      f"{len(r['seats'])} seats, {len(r['turns'])} turns, {len(r['warnings'])} step warnings")
            else:
                print(f"  target {r['target_m']} m -> no loop found")
    print("wrote", dest.relative_to(ROOT))


if __name__ == "__main__":
    main()
