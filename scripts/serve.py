"""Local server for the phone app and the photo labelling page.

Usage: python scripts/serve.py            then open http://localhost:8000/web/  or  http://localhost:8000/label
- /web/...          the phone app
- /label            the labelling page (tools/label.html)
- /photos/<id>.jpg  downloaded street photos (local only, never published)
- /sample           the photo ids to label, with any answers saved so far
- POST /labels      saves your answers to eval/labels.json
"""
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bench_to_bench import sample  # noqa: E402

CITY = "kolkata"
LABELS = ROOT / "eval/labels.json"


def sample_ids():
    return sample.sample_ids(ROOT / f"data/photos_{CITY}.json")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path in ("/label", "/label/"):
            return self._send(200, (ROOT / "tools/label.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/sample":
            saved = json.loads(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}
            return self._send(200, json.dumps({"ids": sample_ids(), "labels": saved}).encode(), "application/json")
        if self.path.startswith("/photos/"):
            name = Path(self.path).name
            photo = ROOT / "data/cache/photos" / CITY / name
            if name.endswith(".jpg") and photo.is_file():
                return self._send(200, photo.read_bytes(), "image/jpeg")
            return self._send(404, b"not found", "text/plain")
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/web/")
            self.end_headers()
            return None
        return super().do_GET()

    def do_POST(self):
        if self.path != "/labels":
            return self._send(404, b"not found", "text/plain")
        labels = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        allowed = set(sample_ids())
        clean = {k: v for k, v in labels.items() if k in allowed and isinstance(v, dict)}
        LABELS.parent.mkdir(parents=True, exist_ok=True)
        LABELS.write_text(json.dumps(clean, indent=1, sort_keys=True), encoding="utf-8")
        return self._send(200, json.dumps({"saved": len(clean)}).encode(), "application/json")

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Serving on http://localhost:{port}/web/  and  http://localhost:{port}/label")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
