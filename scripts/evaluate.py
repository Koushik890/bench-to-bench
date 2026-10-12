"""Step 5: measure how often Gemma is right, how fast it is, and what its seats add to the map.

Usage: python scripts/evaluate.py mainz gemma4:e4b gemma4:e2b
Needs eval/labels_<city>.json (from the labelling page) and data/gemma_<city>_<model>.json for each model.
Writes eval/results_<city>.md and eval/results_<city>.json.

Besides Gemma, the map itself is scored as a "model" for the seat question: it says "seat" when
OpenStreetMap has a bench within 15 m of where the photo was taken.
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench_to_bench import gemma, osm  # noqa: E402
from bench_to_bench.geo import distance_m  # noqa: E402

FIELDS = ["seat", "steps", "broken_surface", "shade"]
MAP_RADIUS_M = 15


def confusion(pairs):
    """pairs: (guess, truth) booleans -> counts and rates."""
    tp = sum(1 for g, t in pairs if g and t)
    fp = sum(1 for g, t in pairs if g and not t)
    fn = sum(1 for g, t in pairs if t and not g)
    tn = sum(1 for g, t in pairs if not g and not t)
    n = tp + fp + fn + tn
    return {
        "correct": tp + tn, "of": n, "accuracy": round((tp + tn) / n, 3) if n else None,
        "true_pos": tp, "false_pos": fp, "false_neg": fn, "true_neg": tn,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
    }


def score_model(city, model, labels):
    results = json.loads((ROOT / f"data/gemma_{city}_{model.replace(':', '-')}.json").read_text(encoding="utf-8"))
    ids = [i for i in labels if i in results]
    usable = [i for i in ids if results[i]["ok"]]
    out = {
        "model": model,
        "photos": len(ids),
        "usable_answers": len(usable),
        "failed": {i: results[i]["problems"] for i in ids if not results[i]["ok"]},
        "seconds_median": round(statistics.median(results[i]["seconds"] for i in ids), 2) if ids else None,
        "seconds_mean": round(statistics.mean(results[i]["seconds"] for i in ids), 2) if ids else None,
        "fields": {f: confusion([(results[i]["answer"][f], labels[i][f]) for i in usable]) for f in FIELDS},
        "mistakes": [{"photo": i, "field": f, "gemma": results[i]["answer"][f], "truth": labels[i][f],
                      "note": results[i]["answer"]["note"]}
                     for i in usable for f in FIELDS if results[i]["answer"][f] != labels[i][f]],
    }
    return out


def score_map(city, labels):
    """The map as a seat detector: a mapped bench within MAP_RADIUS_M of the camera."""
    cities = json.loads((ROOT / "data/cities.json").read_text(encoding="utf-8"))
    seats = osm.load_city(cities[city]["bbox"], ROOT / f"data/cache/osm_{city}.json")["seats"]
    photos = {p["id"]: p for p in json.loads((ROOT / f"data/photos_{city}.json").read_text(encoding="utf-8"))}
    pairs = []
    for i, truth in labels.items():
        here = (photos[i]["lat"], photos[i]["lon"])
        near = any(distance_m(here, (s["lat"], s["lon"])) <= MAP_RADIUS_M for s in seats)
        pairs.append((near, truth["seat"]))
    return confusion(pairs)


def baseline(labels):
    """Accuracy of always answering 'no': the bar Gemma has to clear."""
    return {f: round(sum(not v[f] for v in labels.values()) / len(labels), 3) for f in FIELDS}


def map_comparison(city):
    data = json.loads((ROOT / f"web/data/{city}.json").read_text(encoding="utf-8"))
    if "with_gemma" not in data:
        return None

    def summary(v):
        return {
            "seats": v["seats_total"],
            "coverage_75m": v["coverage_75m"],
            "routes_found": [f"{r['target_m']} m -> {r['length_m']} m, longest gap {r['max_gap_m']} m"
                             for r in v["routes"] if r["found"]],
            "no_route_reason": v.get("no_route_reason"),
        }
    return {"map_only": summary(data["map_only"]), "with_gemma": summary(data["with_gemma"])}


def pct(x):
    return "-" if x is None else f"{x * 100:.0f}%"


def write_markdown(city, models, mapscore, base, maps, labels):
    place = gemma.PLACES[city]
    lines = [f"# Evaluation: Gemma reading street photos from {place}", "",
             f"{len(labels)} Mapillary photos, labelled by hand on the labelling page before looking at Gemma's answers.",
             "Gemma runs locally through Ollama on an RTX 5060 laptop GPU (8 GB).", "",
             "## Accuracy per question", "",
             "| Question | Always \"no\" | " + " | ".join(m["model"] for m in models) + " |",
             "|---|---|" + "---|" * len(models)]
    for f in FIELDS:
        lines.append(f"| {f} | {pct(base[f])} | " + " | ".join(
            f"{pct(m['fields'][f]['accuracy'])} ({m['fields'][f]['correct']}/{m['fields'][f]['of']})" for m in models) + " |")
    lines += ["", "## Finding places to sit", "",
              "| Who | Accuracy | Seats it named that were real (precision) | Real seats it found (recall) | False seats | Missed seats |",
              "|---|---|---|---|---|---|"]
    for name, s in [(m["model"], m["fields"]["seat"]) for m in models] + [(f"Map (bench within {MAP_RADIUS_M} m)", mapscore)]:
        lines.append(f"| {name} | {pct(s['accuracy'])} | {pct(s['precision'])} | {pct(s['recall'])} | {s['false_pos']} | {s['false_neg']} |")
    lines += ["", "## Speed and reliability", "", "| Model | Usable answers | Median seconds per photo | Mean |", "|---|---|---|---|"]
    for m in models:
        lines.append(f"| {m['model']} | {m['usable_answers']}/{m['photos']} | {m['seconds_median']} | {m['seconds_mean']} |")
    if maps:
        mo, wg = maps["map_only"], maps["with_gemma"]
        lines += ["", "## Map alone vs map + Gemma (all photos, main model)", "",
                  "| | Map only | Map + Gemma |", "|---|---|---|",
                  f"| Places to sit | {mo['seats']} | {wg['seats']} |",
                  f"| Streets within 75 m of a seat | {pct(mo['coverage_75m'])} | {pct(wg['coverage_75m'])} |",
                  f"| Walks found (max 150 m between seats) | {', '.join(mo['routes_found']) or 'none'} | {', '.join(wg['routes_found']) or 'none'} |"]
    lines += ["", "## Every mistake", ""]
    for m in models:
        lines += [f"### {m['model']}", "", "| Photo | Question | Gemma said | Truth | Gemma's note |", "|---|---|---|---|---|"]
        for x in m["mistakes"]:
            lines.append(f"| [{x['photo']}](https://www.mapillary.com/app/?pKey={x['photo']}) | {x['field']} | "
                         f"{'yes' if x['gemma'] else 'no'} | {'yes' if x['truth'] else 'no'} | {x['note']} |")
        for i, problems in m["failed"].items():
            lines.append(f"| [{i}](https://www.mapillary.com/app/?pKey={i}) | (no usable answer) | - | - | {'; '.join(problems)[:120]} |")
        lines.append("")
    return "\n".join(lines)


def main():
    city = sys.argv[1]
    models = sys.argv[2:] or ["gemma4:e4b", "gemma4:e2b"]
    labels = json.loads((ROOT / f"eval/labels_{city}.json").read_text(encoding="utf-8"))
    labels = {i: v for i, v in labels.items() if all(f in v for f in FIELDS)}
    if not labels:
        sys.exit("No complete labels yet: finish the labelling page first.")
    scored = [score_model(city, m, labels) for m in models]
    mapscore = score_map(city, labels)
    base = baseline(labels)
    maps = map_comparison(city)
    result = {"city": city, "labels": len(labels), "always_no": base, "models": scored, "map_seat_detector": mapscore, "map": maps}
    (ROOT / f"eval/results_{city}.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    md = write_markdown(city, scored, mapscore, base, maps, labels)
    (ROOT / f"eval/results_{city}.md").write_text(md, encoding="utf-8")
    print(md.split("## Every mistake")[0])


if __name__ == "__main__":
    main()
