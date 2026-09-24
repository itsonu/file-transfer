"""Regenerate the screenshots in docs/screenshots/.

    python scripts/screenshots.py

Needs the e2e extra (``pip install -e '.[e2e]'`` + ``playwright install chromium``).
Starts a throw-away server seeded with sample files, then captures the main
states in light and dark mode on desktop and phone sizes.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
PORT = 5123
URL = f"http://127.0.0.1:{PORT}"

PHOTO_HTML = """
<canvas id=c width=900 height=600></canvas><script>{{
const c = document.getElementById('c').getContext('2d');
const g = c.createLinearGradient(0, 0, 0, 600);
g.addColorStop(0, '{top}'); g.addColorStop(0.62, '{mid}'); g.addColorStop(1, '{bottom}');
c.fillStyle = g; c.fillRect(0, 0, 900, 600);
c.fillStyle = 'rgba(255,240,200,.95)'; c.beginPath(); c.arc(610, 330, 70, 0, 7); c.fill();
c.fillStyle = 'rgba(20,30,60,.55)'; c.fillRect(0, 400, 900, 200);
}}</script>"""

SAMPLES = [
    # name, size in bytes (sparse), minutes ago
    ("Team offsite.mov", 734_003_200, 2),
    ("Q3 Report.pdf", 2_412_000, 14),
    ("Budget 2026.xlsx", 88_400, 55),
    ("Design specs.zip", 48_200_000, 180),
    ("Voice memo.m4a", 3_100_000, 60 * 26),
    ("Keynote.key", 21_900_000, 60 * 24 * 3),
]
PHOTOS = [
    ("Sunset at Big Sur.jpg", ("#ff9a5a", "#ff5e62", "#3b2c5a"), 1),
    ("Golden hour.jpg", ("#2c3e70", "#f7b267", "#1d2b53"), 40),
]


def seed(share: Path, page: Page) -> None:
    now = time.time()
    for name, size, minutes in SAMPLES:
        path = share / name
        with path.open("wb") as fh:
            fh.truncate(size)
        os.utime(path, (now - minutes * 60, now - minutes * 60))
    for name, (top, mid, bottom), minutes in PHOTOS:
        page.set_content(PHOTO_HTML.format(top=top, mid=mid, bottom=bottom))
        page.wait_for_timeout(100)
        data = page.locator("#c").screenshot(type="jpeg", quality=85)
        path = share / name
        path.write_bytes(data)
        os.utime(path, (now - minutes * 60, now - minutes * 60))


def wait_for_image(page: Page, selector: str) -> None:
    img = page.locator(selector)
    for _ in range(100):
        if img.evaluate("el => el.complete && el.naturalWidth > 0"):
            return
        page.wait_for_timeout(50)
    raise RuntimeError(f"{selector} never loaded")


def start_server(share: Path, *args: str) -> subprocess.Popen[bytes]:
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "open_transfer", str(share), "--port", str(PORT),
         "--host", "127.0.0.1", "--no-browser", "--no-qr", "--public-url",
         "http://192.168.1.24:5000", "--allow-host", "*", *args],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{URL}/api/health", timeout=1).close()  # noqa: S310
            return proc
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise RuntimeError("server did not start")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        share = Path(tmp) / "share"
        share.mkdir()
        browser = p.chromium.launch()
        seed(share, browser.new_page())

        big = Path(tmp) / "Wedding photos.zip"
        with big.open("wb") as fh:
            fh.write(os.urandom(40_000_000))
        small = Path(tmp) / "Boarding pass.pdf"
        small.write_bytes(os.urandom(300_000))

        proc = start_server(share)
        try:
            for scheme in ("light", "dark"):
                ctx = browser.new_context(
                    viewport={"width": 1180, "height": 900},
                    device_scale_factor=2,
                    color_scheme=scheme,
                )
                page = ctx.new_page()
                page.goto(URL)
                page.wait_for_selector(".file-row img.is-loaded")
                page.wait_for_timeout(500)
                page.screenshot(path=OUT / f"desktop-{scheme}.png")

                if scheme == "light":
                    cdp = ctx.new_cdp_session(page)
                    cdp.send("Network.enable")
                    cdp.send(
                        "Network.emulateNetworkConditions",
                        {"offline": False, "latency": 20, "downloadThroughput": -1,
                         "uploadThroughput": 6_000_000},
                    )  # fmt: skip
                    page.set_input_files("#file-input", [str(big), str(small)])
                    page.wait_for_timeout(2600)
                    page.screenshot(path=OUT / "sending.png")
                    cdp.send(
                        "Network.emulateNetworkConditions",
                        {"offline": False, "latency": 0, "downloadThroughput": -1,
                         "uploadThroughput": -1},
                    )  # fmt: skip
                    page.wait_for_timeout(6000)

                page.get_by_role("button", name="Add a device").click()
                wait_for_image(page, "#qr-image")
                page.wait_for_timeout(500)
                page.screenshot(path=OUT / f"connect-{scheme}.png")
                ctx.close()

            phone = p.devices["iPhone 15 Pro"]
            for scheme in ("light", "dark"):
                ctx = browser.new_context(**phone, color_scheme=scheme)
                page = ctx.new_page()
                page.goto(URL)
                page.wait_for_selector(".file-row img.is-loaded")
                page.wait_for_timeout(500)
                page.screenshot(path=OUT / f"phone-{scheme}.png")
                ctx.close()
        finally:
            proc.terminate()
            proc.wait()

        proc = start_server(share, "--pin", "2468")
        try:
            ctx = browser.new_context(**p.devices["iPhone 15 Pro"])
            page = ctx.new_page()
            page.goto(URL)
            page.wait_for_selector("#pin-input")
            page.fill("#pin-input", "13")
            page.wait_for_timeout(400)
            page.screenshot(path=OUT / "phone-pin.png")
            ctx.close()
        finally:
            proc.terminate()
            proc.wait()
        browser.close()
    print(f"Screenshots written to {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
