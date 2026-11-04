#!/usr/bin/env python3
"""Serve preview.html at / for a local browser or workspace live preview."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?", 1)[0] == "/":
            self.path = "/preview.html"
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    if not (ROOT / "preview.html").exists():
        parser.error("Run python3 scripts/gen_preview.py first.")
    handler = partial(PreviewHandler, directory=str(ROOT))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Profile preview listening on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
