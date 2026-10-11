"""Let Gemma read every downloaded street photo of a city.

Usage:
  python scripts/read_photos.py kolkata gemma4:e4b            # all photos
  python scripts/read_photos.py kolkata gemma4:e2b --sample   # only the 40 labelled photos

Writes data/gemma_<city>_<model>.json (one result per photo; reruns skip photos with a usable answer).
For the main model, --seats also writes data/gemma_seats_<city>.json, the seats the route planner may use.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench_to_bench import gemma, sample  # noqa: E402


def results_path(city, model):
    return ROOT / f"data/gemma_{city}_{model.replace(':', '-')}.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("model")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sample", action="store_true", help="only the photos on the labelling page")
    ap.add_argument("--seats", action="store_true", help="also write the seats file used by build_city.py")
    args = ap.parse_args()

    photos_json = ROOT / f"data/photos_{args.city}.json"
    photos = sorted(json.loads(photos_json.read_text(encoding="utf-8")), key=lambda p: p["id"])
    if args.sample:
        wanted = set(sample.sample_ids(photos_json))
        photos = [p for p in photos if p["id"] in wanted]
    photos = photos[: args.limit]
    out_path = results_path(args.city, args.model)
    results = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}

    for i, photo in enumerate(photos, 1):
        if results.get(photo["id"], {}).get("ok"):
            continue  # failed photos are tried again on a rerun
        image = ROOT / "data/cache/photos" / args.city / f"{photo['id']}.jpg"
        results[photo["id"]] = gemma.describe_photo(image, args.model)
        r = results[photo["id"]]
        status = "seat" if r["ok"] and r["answer"]["seat"] else ("ok" if r["ok"] else "FAILED " + "; ".join(r["problems"])[:80])
        print(f"{i}/{len(photos)} {photo['id']} {r['seconds']}s {status}", flush=True)
        out_path.write_text(json.dumps(results, indent=1), encoding="utf-8")

    done = [results[p["id"]] for p in photos if p["id"] in results]
    ok = [r for r in done if r["ok"]]
    print(f"{args.model}: {len(ok)}/{len(done)} usable answers, {sum(r['answer']['seat'] for r in ok)} photos with a seat, "
          f"median {sorted(r['seconds'] for r in done)[len(done) // 2]}s per photo")

    if args.seats:
        seats = [{
            "id": f"mapillary/{p['id']}",
            "lat": p["lat"],
            "lon": p["lon"],
            "kind": results[p["id"]]["answer"]["seat_type"],
            "source": "gemma",
            "photo": p["id"],
            "note": results[p["id"]]["answer"]["note"],
        } for p in photos if p["id"] in results and results[p["id"]]["ok"] and results[p["id"]]["answer"]["seat"]]
        seats_path = ROOT / f"data/gemma_seats_{args.city}.json"
        seats_path.write_text(json.dumps(seats, indent=1), encoding="utf-8")
        print(f"{len(seats)} seats -> {seats_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
