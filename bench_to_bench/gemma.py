"""Ask a local Gemma (through Ollama) to describe a street photo, then check its answer.

Gemma only describes what it sees. It never plans a route; plain code decides what to do with the answer.
"""
import base64
import json
import time
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

SEAT_TYPES = ["none", "bench", "tea_stall_bench", "platform_or_ledge", "building_steps", "chair", "other"]

FIELDS = {
    "seat": bool,
    "seat_type": str,
    "steps": bool,
    "broken_surface": bool,
    "shade": bool,
    "note": str,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "seat": {"type": "boolean"},
        "seat_type": {"type": "string", "enum": SEAT_TYPES},
        "steps": {"type": "boolean"},
        "broken_surface": {"type": "boolean"},
        "shade": {"type": "boolean"},
        "note": {"type": "string"},
    },
    "required": list(FIELDS),
}

PROMPT = """You are helping an older man with knee pain plan a walk in Kolkata, India.
Look at this street photo and answer only about what is clearly visible near the camera (within about 20 metres).

seat: true if there is somewhere a tired adult could sit down for a few minutes and that is open to passers-by:
  a bench, a tea-stall bench, a raised concrete platform or low wall ledge at sitting height, the front steps of a
  building or temple, or a chair outside a shop. false if you are not sure.
seat_type: one of none, bench, tea_stall_bench, platform_or_ledge, building_steps, chair, other. Use none when seat is false.
steps: true if the footpath or the way ahead has steps or a kerb higher than about 15 cm that he would have to climb.
broken_surface: true if the footpath or road edge he would walk on is broken, dug up, has potholes or is blocked by rubble.
shade: true if trees or awnings shade the place where he would walk.
note: one short sentence (max 20 words) saying what you based the seat answer on.

Answer with JSON only."""


def validate(answer):
    """Return a list of problems with Gemma's answer (empty list = the answer is usable)."""
    if not isinstance(answer, dict):
        return ["answer is not a JSON object"]
    problems = []
    for key, kind in FIELDS.items():
        if key not in answer:
            problems.append(f"missing {key}")
        elif not isinstance(answer[key], kind):
            problems.append(f"{key} should be {kind.__name__}")
    if not problems:
        if answer["seat_type"] not in SEAT_TYPES:
            problems.append(f"unknown seat_type {answer['seat_type']!r}")
        elif answer["seat"] != (answer["seat_type"] != "none"):
            problems.append("seat and seat_type disagree")
    return problems


def describe_photo(image_path, model, url=OLLAMA_URL, timeout=300):
    """Ask Gemma about one photo.

    Returns {"ok": bool, "answer": dict | None, "problems": [...], "seconds": float, "raw": str}.
    ok is False when Ollama fails, the reply is not JSON, or validate() finds problems.
    """
    image_b64 = base64.b64encode(open(image_path, "rb").read()).decode()
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": PROMPT, "images": [image_b64]}],
        "format": SCHEMA,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_ctx": 4096},
    }).encode()
    started = time.time()
    raw = ""
    try:
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))["message"]["content"]
        answer = json.loads(raw)
    except Exception as exc:
        return {"ok": False, "answer": None, "problems": [f"{type(exc).__name__}: {exc}"],
                "seconds": round(time.time() - started, 2), "raw": raw}
    problems = validate(answer)
    return {"ok": not problems, "answer": answer if not problems else None, "problems": problems,
            "seconds": round(time.time() - started, 2), "raw": raw}
