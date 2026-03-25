"""
Record a GIF of the devcull TUI using Textual's headless Pilot API.
Renders each SVG frame via Playwright, then assembles into a GIF with Pillow.

Usage: python make_gif.py
Output: demo.gif
"""

import asyncio
import sys
import os
import tempfile
from pathlib import Path

# Make sure we can import from this project
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from playwright.sync_api import sync_playwright

DEMO_PATH = Path("C:/Users/eliwo/demo_projects")
OUT_GIF = Path(__file__).parent / "demo.gif"
THUMB_W = 900  # px width for the GIF


async def capture_frames() -> list[tuple[str, int]]:
    """Drive the TUI with Pilot, return (svg_str, hold_ms) pairs."""
    from pro.devcull_tui import CullApp

    app = CullApp(root=DEMO_PATH, older_than=30, min_size_mb=0)
    frames: list[tuple[str, int]] = []

    async with app.run_test(size=(110, 30)) as pilot:
        # Wait for scan to finish (worker thread)
        await pilot.pause(3.0)
        frames.append((app.export_screenshot(), 2000))  # results loaded

        # Select all
        await pilot.press("a")
        await pilot.pause(0.4)
        frames.append((app.export_screenshot(), 1200))

        # Deselect all
        await pilot.press("n")
        await pilot.pause(0.3)
        frames.append((app.export_screenshot(), 800))

        # Select first two rows
        await pilot.press("space")
        await pilot.pause(0.2)
        await pilot.press("down")
        await pilot.pause(0.1)
        await pilot.press("space")
        await pilot.pause(0.3)
        frames.append((app.export_screenshot(), 1500))

    return frames


def svg_to_png(svg: str, pw) -> bytes:
    """Render SVG to PNG bytes using Playwright."""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w",
                                     encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>body{{margin:0;padding:0;background:#1e1e2e;}}</style>
</head><body>{svg}</body></html>""")
        tmp = f.name

    try:
        page = pw.chromium.launch().new_page()
        page.goto(f"file:///{tmp.replace(chr(92), '/')}")
        page.wait_for_load_state("networkidle")
        # Fit viewport to the SVG
        svg_el = page.query_selector("svg")
        if svg_el:
            bb = svg_el.bounding_box()
            page.set_viewport_size({"width": int(bb["width"]) + 4,
                                    "height": int(bb["height"]) + 4})
        png = page.screenshot(full_page=True)
        page.context.browser.close()
        return png
    finally:
        os.unlink(tmp)


def make_gif(frames: list[tuple[str, int]]):
    images: list[Image.Image] = []
    delays: list[int] = []

    with sync_playwright() as pw:
        for svg, hold_ms in frames:
            png_bytes = svg_to_png(svg, pw)
            img = Image.open(__import__("io").BytesIO(png_bytes))
            # Uniform width
            ratio = THUMB_W / img.width
            img = img.resize((THUMB_W, int(img.height * ratio)), Image.LANCZOS)
            images.append(img.convert("RGB"))
            delays.append(hold_ms)

    if not images:
        print("no frames", flush=True)
        return

    # Convert to palette mode for GIF
    pal = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT) for f in images]
    pal[0].save(
        OUT_GIF,
        save_all=True,
        append_images=pal[1:],
        loop=0,
        duration=delays,
        optimize=True,
    )
    print(f"saved {OUT_GIF} ({len(pal)} frames, "
          f"{OUT_GIF.stat().st_size // 1024} KB)", flush=True)


if __name__ == "__main__":
    print("capturing frames…", flush=True)
    frames = asyncio.run(capture_frames())
    print(f"{len(frames)} frames captured, rendering…", flush=True)
    make_gif(frames)
