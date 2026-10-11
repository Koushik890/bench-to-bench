# Bench to Bench

A walk planner for someone with knee pain. It plans a short loop with a place to sit never more than 150 m away, no steps and no rough ground. During the walk the phone stays in a pocket and speaks: "Bench in 80 metres."

Built for the Hacktoberfest 2026 Week 1 "Touch Grass" challenge on DEV.

## Same app, two cities

- **Mainz-Neustadt (55118):** OpenStreetMap already knows 431 benches here, so routes come straight from the map.
- **Kolkata, Kalighat-Hazra:** OpenStreetMap knows **0** places to sit. Gemma looks at street photos from Mapillary and finds them: tea-stall benches, raised platforms, the front steps of buildings.

**Gemma only describes photos. Plain code makes every route decision.** Every Gemma answer is checked against a fixed format; if it does not fit, the photo is skipped and counted as a failure, never guessed.

## How it works

```
OpenStreetMap streets ──> walking graph (no steps, gravel, cobblestones, private paths)
OpenStreetMap benches ──┐
Gemma seats from photos ┴─> seat-to-seat loop, every stretch <= 150 m ──> web/data/<city>.json
                                                                              │
                         phone page: map, "Start walk", black screen, GPS, spoken cues
```

| Folder | What |
|---|---|
| `bench_to_bench/` | Services: `osm` (Overpass), `walkgraph` (walking rules), `route` (loops, coverage), `mapillary`, `gemma` (Ollama call + answer check) |
| `scripts/` | Steps you run: `build_city.py`, `fetch_photos.py`, `read_photos.py`, `evaluate.py`, `serve.py` |
| `web/` | The phone app (static, works on GitHub Pages). `cues.js` decides what to say. |
| `tools/label.html` | Page to label photos by hand for the evaluation |
| `eval/` | Labels and results |

## Run it

Needs Python 3.12, Node 20+ (tests only) and [Ollama](https://ollama.com).

```bash
python -m venv .venv
.venv/Scripts/python -m pip install pytest      # tests only; the app uses the standard library

# Mainz from the map alone
.venv/Scripts/python scripts/build_city.py mainz

# Kolkata: photos, Gemma, then routes with Gemma's seats
echo MAPILLARY_TOKEN=MLY|... >> .env
.venv/Scripts/python scripts/fetch_photos.py kolkata
ollama pull gemma4:e4b
.venv/Scripts/python scripts/read_photos.py kolkata gemma4:e4b --seats
.venv/Scripts/python scripts/build_city.py kolkata --gemma-seats data/gemma_seats_kolkata.json

# Phone app and labelling page
.venv/Scripts/python scripts/serve.py      # http://localhost:8000/web/  and  /label
```

Tests: `.venv/Scripts/python -m pytest -q` and `node --test tests/cues.test.mjs`.

## The voice

The phone's built-in voice (Web Speech API in Chrome) reads the cues. No app install. Tap "Start walk" once (phones only allow sound after a tap); the screen stays on but black so GPS and voice keep working in a pocket. "Practice walk" moves along the route by itself, eight times faster than walking, to hear every cue at home.

## Credits

- Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, ODbL.
- Street photos from [Mapillary](https://www.mapillary.com), CC BY-SA 4.0. Photos are not stored in this repo; `data/photos_kolkata.json` lists their ids, places and contributors.
- Map display: [Leaflet](https://leafletjs.com).
- Places to sit in photos: Gemma, running locally through Ollama.
