#!/usr/bin/env python3
"""Run this on the Mac (this project). Saves photos uploaded by the Pi into captures/."""

from __future__ import annotations

import argparse
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
CAPTURES_DIR = PROJECT_ROOT / "captures"


class UploadHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/upload":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            self.send_error(400, "Empty body")
            return

        content_type = self.headers.get("Content-Type", "")
        if "image/jpeg" not in content_type and "application/octet-stream" not in content_type:
            self.send_error(415, "Send JPEG as image/jpeg")
            return

        body = self.rfile.read(length)
        if not body:
            self.send_error(400, "Empty body")
            return

        CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = CAPTURES_DIR / f"pi_{stamp}.jpg"
        dest.write_bytes(body)
        latest = CAPTURES_DIR / "latest.jpg"
        latest.write_bytes(body)

        print(f"saved {dest} ({len(body)} bytes)", flush=True)
        self.send_response(201)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(dest.name.encode("utf-8"))

    def log_message(self, format: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


def main() -> None:
    parser = argparse.ArgumentParser(description="Receive Pi camera JPEGs into captures/")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), UploadHandler)
    print(f"listening on http://{args.host}:{args.port}/upload", flush=True)
    print(f"saving to {CAPTURES_DIR}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped", flush=True)


if __name__ == "__main__":
    main()
