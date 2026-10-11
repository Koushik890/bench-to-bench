"""Step 5: measure how often Gemma is right, how fast it is, and what its seats add to the map.

Usage: python scripts/evaluate.py gemma4:e4b gemma4:e2b
Needs eval/labels.json (from the labelling page), data/gemma_kolkata_<model>.json for each model,
and web/data/kolkata.json built with --gemma-seats. Writes eval/results.md and eval/results.json.
"""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ["seat", "steps", "broken_surface", "shade"]
CITY = "kolkata"


def score_model(model, labels):
    results = json.loads((ROOT / f"data/gemma_{CITY}_{model.replace(':', '-')}.json").read_text(encoding="utf-8"))
    ids = [i for i in labels if i in results]
    usable = [i for i in ids if results[i]["ok"]]
    out = {
        "model": model,
        "photos": len(ids),
        "usable_answers": len(usable),
        "failed": {i: results[i]["problems"] for i in ids if not results[i]["ok"]},
        "seconds_median": round(statistics.median(results[i]["seconds"] for i in ids), 2) if ids else None,
        "seconds_mean": round(statistics.mean(results[i]["seconds"] for i in ids), 2) if ids else None,
        "fields": {},
        "mistakes": [],
    }
    for f in FIELDS:
        tp = fp = fn = tn = 0
        for i in usable:
            guess, truth = results[i]["answer"][f], labels[i][f]
            tp += guess and truth
            fp += guess and not truth
            fn += truth and not guess
            tn += not guess and not truth
            if guess != truth:
                out["mistakes"].append({"photo": i, "field": f, "gemma": guess, "truth": truth,
                                        "note": results[i]["answer"]["note"]})
        n = tp + fp + fn + tn
        out["fields"][f] = {
            "correct": tp + tn, "of": n, "accuracy": round((tp + tn) / n, 3) if n else None,
            "true_pos": tp, "false_pos": fp, "false_neg": fn, "true_neg": tn,
            "precision": round(tp / (tp + fp), 3) if tp + fp else None,
            "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        }
    return out


def baseline(labels):
    """Accuracy of always answering 'no': the bar Gemma has to clear."""
    return {f: round(sum(not v[f] for v in labels.values()) / len(labels), 3) for f in FIELDS}


def map_comparison():
    data = json.loads((ROOT / f"web/data/{CITY}.json").read_text(encoding="utf-8"))
    def summary(v):
        found = [r for r in v["routes"] if r["found"]]
        return {
            "seats": v["seats_total"],
            "coverage_75m": v["coverage_75m"],
            "routes_found": [f"{r['target_m']} m -> {r['length_m']} m, longest gap {r['max_gap_m']} m" for r in found],
            "no_route_reason": v.get("no_route_reason"),
        }
    return {"map_only": summary(data["map_only"]),
            "with_gemma": summary(data["with_gemma"]) if "with_gemma" in data else None,
            "gemma_seats_added": data.get("gemma_seats_added"),
            "gemma_seats_not_on_a_street": data.get("gemma_seats_not_on_a_street")}


def pct(x):
    return "-" if x is None else f"{x * 100:.0f}%"


def write_markdown(models, base, maps, labels):
    lines = ["# Evaluation: Gemma reading Kolkata street photos", "",
             f"{len(labels)} photos from Kalighat-Hazra, labelled by hand on the labelling page before looking at Gemma's answers.",
             "Gemma runs locally through Ollama on an RTX 5060 laptop GPU (8 GB).", "",
             "## Accuracy per question", "",
             "| Question | Always \"no\" | " + " | ".join(m["model"] for m in models) + " |",
             "|---|---|" + "---|" * len(models)]
    for f in FIELDS:
        lines.append(f"| {f} | {pct(base[f])} | " + " | ".join(
            f"{pct(m['fields'][f]['accuracy'])} ({m['fields'][f]['correct']}/{m['fields'][f]['of']})" for m in models) + " |")
    lines += ["", "## Finding places to sit", "",
              "| Model | Seats found that were real (precision) | Real seats found (recall) | False seats | Missed seats |",
              "|---|---|---|---|---|"]
    for m in models:
        s = m["fields"]["seat"]
        lines.append(f"| {m['model']} | {pct(s['precision'])} | {pct(s['recall'])} | {s['false_pos']} | {s['false_neg']} |")
    lines += ["", "## Speed and reliability", "", "| Model | Usable answers | Median seconds per photo | Mean |", "|---|---|---|---|"]
    for m in models:
        lines.append(f"| {m['model']} | {m['usable_answers']}/{m['photos']} | {m['seconds_median']} | {m['seconds_mean']} |")
    lines += ["", "## Map alone vs map + Gemma (all photos, main model)", "",
              "| | Map only | Map + Gemma |", "|---|---|---|"]
    mo, wg = maps["map_only"], maps["with_gemma"] or {}
    lines.append(f"| Places to sit | {mo['seats']} | {wg.get('seats', '-')} |")
    lines.append(f"| Streets within 75 m of a seat | {pct(mo['coverage_75m'])} | {pct(wg.get('coverage_75m'))} |")
    lines.append(f"| Walks found (max 150 m between seats) | {', '.join(mo['routes_found']) or 'none'} | {', '.join(wg.get('routes_found', [])) or 'none'} |")
    if wg.get("no_route_reason"):
        lines.append(f"| Why no walk | {mo.get('no_route_reason') or '-'} | {wg['no_route_reason']} |")
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
    models = sys.argv[1:] or ["gemma4:e4b", "gemma4:e2b"]
    labels_path = ROOT / "eval/labels.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    labels = {i: v for i, v in labels.items() if all(f in v for f in FIELDS)}
    if not labels:
        sys.exit("No complete labels yet: finish the labelling page first.")
    scored = [score_model(m, labels) for m in models]
    base = baseline(labels)
    maps = map_comparison()
    (ROOT / "eval/results.json").write_text(json.dumps({"labels": len(labels), "always_no": base, "models": scored, "map": maps}, indent=1), encoding="utf-8")
    (ROOT / "eval/results.md").write_text(write_markdown(scored, base, maps, labels), encoding="utf-8")
    print((ROOT / "eval/results.md").read_text(encoding="utf-8").split("## Every mistake")[0])


if __name__ == "__main__":
    main()
