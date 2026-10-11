import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench_to_bench import route, walkgraph  # noqa: E402
from bench_to_bench.geo import distance_m  # noqa: E402

# A 6 x 6 street grid with ~100 m blocks around (50.0, 8.0).
STEP = 0.0009  # ~100 m north-south


def grid_ways(n=6, extra_tags=None):
    def nid(i, j):
        return i * 100 + j

    def coord(i, j):
        return (50.0 + i * STEP, 8.0 + j * STEP * 1.55)

    ways, wid = [], 1
    for i in range(n):
        for j in range(n - 1):
            ways.append({"id": wid, "nodes": [nid(i, j), nid(i, j + 1)], "coords": [coord(i, j), coord(i, j + 1)],
                         "tags": {"highway": "residential", **((extra_tags or {}).get((i, j, "h"), {}))}})
            wid += 1
    for j in range(n):
        for i in range(n - 1):
            ways.append({"id": wid, "nodes": [nid(i, j), nid(i + 1, j)], "coords": [coord(i, j), coord(i + 1, j)],
                         "tags": {"highway": "residential", **((extra_tags or {}).get((i, j, "v"), {}))}})
            wid += 1
    return ways, coord


def seats_at(cells, coord):
    return [{"id": f"s{i}{j}", "lat": coord(i, j)[0] + 0.00001, "lon": coord(i, j)[1], "kind": "bench", "source": "map"}
            for i, j in cells]


def test_classify_refuses_steps_rough_and_private():
    assert walkgraph.classify({"highway": "steps"})[:2] == (False, "steps")
    assert walkgraph.classify({"highway": "footway", "surface": "gravel"})[:2] == (False, "rough surface")
    assert walkgraph.classify({"highway": "service", "access": "private"})[:2] == (False, "no access")
    assert walkgraph.classify({"highway": "footway", "incline": "12%"})[:2] == (False, "steep")
    assert walkgraph.classify({"highway": "residential"}) == (True, None, 1.0)
    assert walkgraph.classify({"highway": "primary"})[2] > 1


def test_steps_are_left_out_of_the_graph_but_remembered():
    ways, _ = grid_ways(3, {(0, 0, "h"): {"highway": "steps"}})
    g = walkgraph.build(ways)
    assert 1 not in [n for n, _, _ in g["adj"].get(0, [])]
    assert g["refused"]["steps"] > 90
    assert 0 in g["steps_nodes"] and 1 in g["steps_nodes"]


def test_loop_keeps_every_gap_under_the_limit_and_closes():
    ways, coord = grid_ways()
    g = walkgraph.build(ways)
    cells = [(i, j) for i in range(6) for j in range(6) if (i + j) % 2 == 0]
    seats, dropped = walkgraph.attach_points(g, seats_at(cells, coord))
    assert not dropped
    nodes = sorted({s["node"] for s in seats})
    loop = route.find_loop(g, nodes, nodes[0], 1000, max_gap=250)
    assert loop is not None
    assert loop["nodes"][0] == loop["nodes"][-1]
    assert 850 <= loop["length_m"] <= 1300
    info = route.describe(g, loop, seats)
    assert info["max_gap_m"] <= 250
    assert info["seats"][0]["at_m"] == 0
    # consecutive path points are real street neighbours
    for a, b in zip(loop["nodes"], loop["nodes"][1:]):
        assert b in [n for n, _, _ in g["adj"][a]]


def test_no_loop_when_seats_are_too_far_apart():
    ways, coord = grid_ways()
    g = walkgraph.build(ways)
    seats, _ = walkgraph.attach_points(g, seats_at([(0, 0), (5, 5)], coord))
    nodes = sorted({s["node"] for s in seats})
    assert route.find_loop(g, nodes, nodes[0], 1000, max_gap=150) is None


def test_coverage_grows_with_more_seats():
    ways, coord = grid_ways()
    g = walkgraph.build(ways)
    few, _ = walkgraph.attach_points(g, seats_at([(0, 0)], coord))
    many, _ = walkgraph.attach_points(g, seats_at([(i, j) for i in range(0, 6, 2) for j in range(0, 6, 2)], coord))
    c0 = route.coverage(g, [], 75)
    c1 = route.coverage(g, [s["node"] for s in few], 75)
    c2 = route.coverage(g, [s["node"] for s in many], 75)
    assert c0 == 0 and 0 < c1 < c2 <= 1


def test_turns_are_detected_at_junctions():
    ways, coord = grid_ways()
    g = walkgraph.build(ways)
    # walk east along row 1 then turn north (left when heading east) at column 2
    nodes = [100, 101, 102, 202, 302]
    info = route.describe(g, {"nodes": nodes, "seat_stops": [], "length_m": 0}, [])
    assert [t["dir"] for t in info["turns"]] == ["left"]
    assert abs(info["turns"][0]["at_m"] - distance_m(coord(1, 0), coord(1, 2))) < 2
