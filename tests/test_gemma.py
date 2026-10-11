import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench_to_bench import gemma  # noqa: E402

GOOD = {"seat": True, "seat_type": "tea_stall_bench", "steps": False, "broken_surface": False, "shade": True,
        "note": "Wooden bench in front of a tea stall."}


def test_validate_accepts_a_good_answer():
    assert gemma.validate(GOOD) == []


def test_validate_rejects_bad_answers():
    assert gemma.validate("yes") == ["answer is not a JSON object"]
    assert "missing shade" in gemma.validate({k: v for k, v in GOOD.items() if k != "shade"})
    assert "seat should be bool" in gemma.validate({**GOOD, "seat": "true"})
    assert gemma.validate({**GOOD, "seat_type": "sofa"}) == ["unknown seat_type 'sofa'"]
    assert gemma.validate({**GOOD, "seat": False}) == ["seat and seat_type disagree"]


def fake_ollama(reply_text):
    """Start a tiny HTTP server that answers like Ollama's /api/chat with reply_text."""
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = json.dumps({"message": {"content": reply_text}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/api/chat"


def photo(tmp_path):
    p = tmp_path / "photo.jpg"
    p.write_bytes(b"\xff\xd8not really a jpeg")
    return p


def test_describe_photo_returns_checked_answer(tmp_path):
    server, url = fake_ollama(json.dumps(GOOD))
    try:
        r = gemma.describe_photo(photo(tmp_path), "gemma4:e4b", url=url)
    finally:
        server.shutdown()
    assert r["ok"] and r["answer"] == GOOD and r["problems"] == []


def test_describe_photo_says_so_when_gemma_answers_badly(tmp_path):
    server, url = fake_ollama("I think there is a bench")
    try:
        r = gemma.describe_photo(photo(tmp_path), "gemma4:e4b", url=url)
    finally:
        server.shutdown()
    assert not r["ok"] and r["answer"] is None and "JSONDecodeError" in r["problems"][0]
    assert r["raw"] == "I think there is a bench"


def test_describe_photo_says_so_when_ollama_is_down(tmp_path):
    r = gemma.describe_photo(photo(tmp_path), "gemma4:e4b", url="http://127.0.0.1:9/api/chat", timeout=3)
    assert not r["ok"] and r["problems"]
