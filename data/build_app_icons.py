"""Render the editable SVG app mark to Android PNG sizes: uv run python data/build_app_icons.py."""

from pathlib import Path
import pymupdf

icons = Path(__file__).resolve().parent.parent / "icons"
with pymupdf.open(icons / "icon.svg") as document:
    page = document[0]
    for filename, size in (("icon-192.png", 192), ("icon-512.png", 512),
                           ("icon-maskable-512.png", 512)):
        page.get_pixmap(matrix=pymupdf.Matrix(size / page.rect.width, size / page.rect.height),
                        alpha=False).save(icons / filename)
        print(f"Wrote {filename}")
