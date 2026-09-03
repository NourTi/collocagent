"""Dependency-free local HTTP API and browser UI for CollocAgent."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .agents import CollocAgent
from .corpus import CorpusIndex

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules.json"
INDEX = Path(os.getenv("COLLOCAGENT_INDEX", ROOT / "data" / "collocagent.sqlite3"))
DEMO = ROOT / "data" / "demo_corpus.txt"
WEB = ROOT / "web" / "index.html"


def ensure_index() -> None:
    if not INDEX.exists():
        CorpusIndex(INDEX).build(
            [DEMO],
            corpus_name="Bundled synthetic demo corpus (not research evidence)",
            window=4,
        )


class Handler(BaseHTTPRequestHandler):
    agent: CollocAgent

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, WEB.read_bytes(), "text/html; charset=utf-8")
            return
        if path == "/health":
            payload = json.dumps(
                {"status": "ok", "system": "CollocAgent", "version": "0.1.0"}
            ).encode()
            self._send(200, payload, "application/json")
            return
        self._send(404, b'{"error":"not found"}', "application/json")

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/analyze":
            self._send(404, b'{"error":"not found"}', "application/json")
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 1_000_000:
                raise ValueError("Request body must be between 1 byte and 1 MB")
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            result = self.agent.analyze(str(data.get("text", "")))
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except Exception as exc:  # API boundary
            body = json.dumps({"error": str(exc)}).encode("utf-8")
            self._send(400, body, "application/json; charset=utf-8")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[collocagent] {self.address_string()} - {fmt % args}")


def main() -> None:
    ensure_index()
    Handler.agent = CollocAgent(RULES, INDEX)
    host = os.getenv("COLLOCAGENT_HOST", "127.0.0.1")
    # Container platforms (Render, Cloud Run, Fly, Heroku) inject the port to
    # bind as PORT. COLLOCAGENT_PORT keeps precedence for local runs.
    port = int(os.getenv("COLLOCAGENT_PORT") or os.getenv("PORT") or "8000")
    print(f"CollocAgent running at http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
