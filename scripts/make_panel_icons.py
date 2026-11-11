"""Render the panel's PWA icons: the aperture mark in ivory on the studio's ink colour.

Run once when the mark or the palette changes (needs Pillow, not a project dependency):

    uv run --with pillow python scripts/make_panel_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "frontend" / "public"
INK, IVORY = (43, 46, 39), (255, 254, 251)
# The aperture icon on a 24-unit grid: a circle of radius 10 and six blades.
BLADES = [
    ((14.31, 8), (20.05, 17.94)),
    ((9.69, 8), (21.17, 8)),
    ((7.38, 12), (13.12, 2.06)),
    ((9.69, 16), (3.95, 6.06)),
    ((14.31, 16), (2.83, 16)),
    ((16.62, 12), (10.88, 21.94)),
]
SUPERSAMPLE = 4


def render(size: int, mark: float, rounded: bool) -> Image.Image:
    """`mark` is the share of the canvas the 24-unit grid occupies."""
    side = size * SUPERSAMPLE
    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = side * 0.22 if rounded else 0
    draw.rounded_rectangle((0, 0, side - 1, side - 1), radius=radius, fill=INK)
    unit = side * mark / 24
    offset = (side - 24 * unit) / 2
    stroke = max(2, round(unit * 1.6))

    def point(x, y):
        return offset + x * unit, offset + y * unit

    cx, cy = point(12, 12)
    r = 10 * unit + stroke / 2  # Pillow strokes inwards; the mark's stroke is centred.
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=IVORY, width=stroke)
    for start, end in BLADES:
        a, b = point(*start), point(*end)
        draw.line((a, b), fill=IVORY, width=stroke)
        for x, y in (a, b):  # round caps
            draw.ellipse(
                (x - stroke / 2, y - stroke / 2, x + stroke / 2, y + stroke / 2), fill=IVORY
            )
    return image.resize((size, size), Image.LANCZOS)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    render(192, 0.62, rounded=True).save(OUT / "icon-192.png", optimize=True)
    render(512, 0.62, rounded=True).save(OUT / "icon-512.png", optimize=True)
    # Maskable: full-bleed background, mark inside the central safe zone.
    render(512, 0.5, rounded=False).save(OUT / "icon-maskable-512.png", optimize=True)
    render(180, 0.62, rounded=False).convert("RGB").save(
        OUT / "apple-touch-icon.png", optimize=True
    )


if __name__ == "__main__":
    main()
