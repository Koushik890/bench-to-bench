"""Find and download street-level photos from Mapillary (images are CC BY-SA 4.0)."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.mapillary.com/images"
FIELDS = "id,captured_at,compass_angle,geometry,thumb_1024_url,is_pano,creator"


def list_images(bbox, token, limit=2000):
    """Images inside bbox = (south, west, north, east). Returns a list of plain dicts."""
    s, w, n, e = bbox
    query = urllib.parse.urlencode({"fields": FIELDS, "bbox": f"{w},{s},{e},{n}", "limit": limit})
    req = urllib.request.Request(f"{API}?{query}", headers={"Authorization": f"OAuth {token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    images = []
    for im in data.get("data", []):
        lon, lat = im["geometry"]["coordinates"]
        images.append({
            "id": im["id"],
            "lat": lat,
            "lon": lon,
            "captured_at": im.get("captured_at"),
            "compass": im.get("compass_angle"),
            "pano": bool(im.get("is_pano")),
            "creator": (im.get("creator") or {}).get("username"),
            "thumb_url": im.get("thumb_1024_url"),
            "page": f"https://www.mapillary.com/app/?pKey={im['id']}",
        })
    return images


def download(image, folder):
    """Save the 1024 px thumbnail as folder/<id>.jpg (skips files already there). Returns the path."""
    path = Path(folder) / f"{image['id']}.jpg"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(image["thumb_url"], timeout=60) as resp:
            path.write_bytes(resp.read())
    return path
