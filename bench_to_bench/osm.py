"""Fetch and parse OpenStreetMap data (streets, benches, toilets) through the Overpass API."""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
USER_AGENT = "bench-to-bench/0.1 (Hacktoberfest 2026 project; github.com/Koushik890/bench-to-bench)"

# Things a tired walker can sit on, as OSM tags.
SEAT_TAGS = [("amenity", "bench"), ("leisure", "picnic_table"), ("amenity", "shelter")]


def build_query(bbox):
    """Overpass QL for every street plus seats and toilets inside bbox = (south, west, north, east)."""
    s, w, n, e = bbox
    b = f"({s},{w},{n},{e})"
    seat_parts = "".join(f'node["{k}"="{v}"]{b};' for k, v in SEAT_TAGS)
    return (
        "[out:json][timeout:120];"
        f'way["highway"]{b};out body geom;'
        f'({seat_parts}node["amenity"="toilets"]{b};);out body;'
    )


def fetch_overpass(query, cache_path, retries_per_server=2):
    """Run an Overpass query, trying each mirror; cache the raw JSON at cache_path."""
    cache_path = Path(cache_path)
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    errors = []
    body = urllib.parse.urlencode({"data": query}).encode()
    for url in OVERPASS_URLS:
        for attempt in range(retries_per_server):
            try:
                req = urllib.request.Request(url, data=body, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=180) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(raw), encoding="utf-8")
                return raw
            except Exception as exc:  # network errors and Overpass 429/504 are common; try the next mirror
                errors.append(f"{url} try {attempt + 1}: {exc}")
                time.sleep(3)
    raise RuntimeError("All Overpass servers failed:\n" + "\n".join(errors))


def parse(raw):
    """Turn raw Overpass JSON into {'ways': [...], 'seats': [...], 'toilets': [...]}."""
    ways, seats, toilets = [], [], []
    for el in raw.get("elements", []):
        tags = el.get("tags", {})
        if el["type"] == "way" and "geometry" in el and "highway" in tags:
            ways.append({
                "id": el["id"],
                "nodes": el["nodes"],
                "coords": [(g["lat"], g["lon"]) for g in el["geometry"]],
                "tags": tags,
            })
        elif el["type"] == "node":
            point = (el["lat"], el["lon"])
            if tags.get("amenity") == "toilets":
                toilets.append({"id": f"osm/{el['id']}", "lat": point[0], "lon": point[1]})
            if any(tags.get(k) == v for k, v in SEAT_TAGS):
                kind = "bench" if tags.get("amenity") == "bench" else tags.get("leisure") or tags.get("amenity")
                seats.append({
                    "id": f"osm/{el['id']}",
                    "lat": point[0],
                    "lon": point[1],
                    "kind": kind,
                    "backrest": tags.get("backrest"),
                    "source": "map",
                })
    return {"ways": ways, "seats": seats, "toilets": toilets}


def load_city(bbox, cache_path):
    """Fetch (or read cached) OSM data for bbox and parse it."""
    return parse(fetch_overpass(build_query(bbox), cache_path))
