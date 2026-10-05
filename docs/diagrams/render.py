"""Render the HTML diagram sources to high-resolution PNGs with headless Chromium.

Usage:
    python docs/diagrams/render.py            # render every src/*.html
    python docs/diagrams/render.py 01-architecture

Each source is a self-contained 1440x1040 HTML page. Output lands next to it as a 2x PNG.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"
WIDTH, HEIGHT, SCALE = 1440, 1040, 2


def render(stem: str) -> Path:
    html = SRC / f"{stem}.html"
    out = HERE / f"{stem}.png"
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        page = browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=SCALE
        )
        page.goto(html.as_uri(), wait_until="networkidle")
        try:
            page.evaluate("document.fonts.ready")
        except Exception:
            pass
        page.wait_for_timeout(600)
        page.screenshot(path=str(out), clip={"x": 0, "y": 0, "width": WIDTH, "height": HEIGHT})
        browser.close()
    return out


def main() -> int:
    stems = sys.argv[1:] or sorted(p.stem for p in SRC.glob("*.html"))
    for stem in stems:
        out = render(stem)
        print(f"rendered {out.name} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
