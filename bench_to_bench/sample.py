"""The fixed set of photos labelled by hand for the evaluation."""
import json
import random
from pathlib import Path

SAMPLE_SIZE = 40
SEED = 2026


def sample_ids(photos_json, size=SAMPLE_SIZE, seed=SEED):
    """The same photo ids every time: a seeded random pick from all downloaded photos."""
    photos = json.loads(Path(photos_json).read_text(encoding="utf-8"))
    return random.Random(seed).sample(sorted(p["id"] for p in photos), size)
