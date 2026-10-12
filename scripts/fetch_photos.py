"""Download Mapillary street photos for a city into data/cache/photos/<city>/.

Usage:
  python scripts/fetch_photos.py kolkata
  python scripts/fetch_photos.py mainz --since 2025 --max 150

Needs MAPILLARY_TOKEN in .env. Writes data/photos_<city>.json (ids, places and credits, no image bytes).
--max keeps a seeded random pick so busy cities stay a manageable size.
"""
import argparse
import datetime
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench_to_bench import mapillary  # noqa: E402
from bench_to_bench.env import read_env  # noqa: E402


def year_of(image):
    return datetime.datetime.fromtimestamp(image["captured_at"] / 1000, datetime.UTC).year


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("--since", type=int, help="only photos taken in this year or later")
    ap.add_argument("--max", type=int, help="keep at most this many photos (seeded random pick)")
    args = ap.parse_args()

    city = json.loads((ROOT / "data/cities.json").read_text(encoding="utf-8"))[args.city]
    token = read_env(ROOT / ".env").get("MAPILLARY_TOKEN")
    if not token:
        sys.exit("MAPILLARY_TOKEN is missing from .env")

    images = [im for im in mapillary.list_images_tiled(city["bbox"], token) if not im["pano"]]
    if args.since:
        images = [im for im in images if year_of(im) >= args.since]
    if args.max and len(images) > args.max:
        images = random.Random(2026).sample(sorted(images, key=lambda im: im["id"]), args.max)

    folder = ROOT / "data/cache/photos" / args.city
    for i, im in enumerate(images, 1):
        mapillary.download(im, folder)
        print(f"\r{i}/{len(images)} photos", end="", flush=True)
    print()
    for im in images:
        im.pop("thumb_url")  # signed URL that expires; the id and page link are enough
        im["year"] = year_of(im)
    out = ROOT / f"data/photos_{args.city}.json"
    out.write_text(json.dumps(images, indent=1), encoding="utf-8")
    years = sorted({im["year"] for im in images})
    print(f"{len(images)} photos ({years[0]}-{years[-1]}) by {len({im['creator'] for im in images})} contributors -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
