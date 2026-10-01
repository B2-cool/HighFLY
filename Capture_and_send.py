#!/usr/bin/env python3
"""Run this on the Raspberry Pi Zero with the HQ camera.

Takes a photo every 30 seconds and POSTs it to the Mac receiver.

"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def capture_with_picamera2(dest: Path, width: int, height: int, picam2) -> None:
    picam2.capture_file(str(dest))


def start_picamera2(width: int, height: int):
    from picamera2 import Picamera2

    picam2 = Picamera2()
    config = picam2.create_still_configuration(main={"size": (width, height)})
    picam2.configure(config)
    picam2.start()
    time.sleep(1.0)
    return picam2


def capture_with_rpicam(dest: Path, width: int, height: int) -> None:
    for binary in ("rpicam-still", "libcamera-still"):
        try:
            subprocess.run(
                [
                    binary,
                    "--nopreview",
                    "-t",
                    "800",
                    "--width",
                    str(width),
                    "--height",
                    str(height),
                    "-o",
                    str(dest),
                ],
                check=True,
                capture_output=True,
            )
            return
        except FileNotFoundError:
            continue
        except subprocess.CalledProcessError as exc:
            err = (exc.stderr or b"").decode("utf-8", errors="replace")
            raise RuntimeError(f"{binary} failed: {err}") from exc
    raise RuntimeError("Install picamera2 or rpicam-still on the Pi")


def upload_jpeg(url: str, path: Path, timeout: float) -> None:
    data = path.read_bytes()
    request = Request(url, data=data, method="POST")
    request.add_header("Content-Type", "image/jpeg")
    request.add_header("Content-Length", str(len(data)))
    with urlopen(request, timeout=timeout) as response:
        response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture HQ camera stills and send them to the Mac")
    parser.add_argument(
        "--url",
        required=True,
        help="",
    )
    parser.add_argument("--interval", type=float, default=30.0, help="Seconds between photos")
    parser.add_argument("--width", type=int, default=2028)
    parser.add_argument("--height", type=int, default=1520)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    picam2 = None
    try:
        picam2 = start_picamera2(args.width, args.height)
        print("using picamera2", flush=True)
    except Exception as exc:
        print(f"picamera2 unavailable ({exc}); falling back to rpicam-still", flush=True)

    print(f"sending a photo every {args.interval}s to {args.url}", flush=True)
    while True:
        started = time.monotonic()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            dest = Path(tmp.name)
        try:
            if picam2 is not None:
                capture_with_picamera2(dest, args.width, args.height, picam2)
            else:
                capture_with_rpicam(dest, args.width, args.height)
            upload_jpeg(args.url, dest, args.timeout)
            print(f"uploaded {dest.stat().st_size} bytes", flush=True)
        except URLError as exc:
            print(f"upload failed: {exc}", flush=True)
        except Exception as exc:
            print(f"capture/send failed: {exc}", flush=True)
        finally:
            dest.unlink(missing_ok=True)

        elapsed = time.monotonic() - started
        sleep_for = args.interval - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
