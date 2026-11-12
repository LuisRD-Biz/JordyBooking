"""Render the panel's icons: the "JF" monogram in crema on espresso with a calabaza rule.

Run once when the mark or the palette changes (needs Pillow, not a project dependency):

    uv run --no-project --with pillow python scripts/make_panel_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "frontend"
OUT = ROOT / "public"
FONT = ROOT / "brand" / "Chewy-Regular.ttf"
ESPRESSO, CREMA, CALABAZA = (59, 36, 24), (246, 235, 221), (217, 119, 43)
SUPERSAMPLE = 4
SLANT = 0.14  # Same lean as the monogram in the interface (skewX(-8deg)).


def render(size: int, mark: float, rounded: bool) -> Image.Image:
    """`mark` is the share of the canvas height taken by the letters."""
    side = size * SUPERSAMPLE
    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    radius = side * 0.22 if rounded else 0
    draw.rounded_rectangle((0, 0, side - 1, side - 1), radius=radius, fill=ESPRESSO)

    # Letters on their own layer so they can lean without bending the background.
    letters = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    font = ImageFont.truetype(str(FONT), round(side * mark))
    pen = ImageDraw.Draw(letters)
    left, top, right, bottom = pen.textbbox((0, 0), "JF", font=font)
    x = (side - (right - left)) / 2 - left
    y = (side - (bottom - top)) / 2 - top - side * 0.03
    pen.text((x, y), "JF", font=font, fill=CREMA)
    letters = letters.transform(
        (side, side), Image.AFFINE, (1, SLANT, -SLANT * side / 2, 0, 1, 0), Image.BICUBIC
    )
    image.alpha_composite(letters)

    rule = side * 0.045
    inset = side * (0.2 if rounded else 0.28)
    base = side * (0.8 if rounded else 0.74)
    draw.rounded_rectangle((inset, base, side - inset, base + rule), radius=rule / 2, fill=CALABAZA)
    return image.resize((size, size), Image.LANCZOS)


def main():
    render(192, 0.5, rounded=True).save(OUT / "icon-192.png", optimize=True)
    render(512, 0.5, rounded=True).save(OUT / "icon-512.png", optimize=True)
    # Maskable: full-bleed background, mark inside the central safe zone.
    render(512, 0.36, rounded=False).save(OUT / "icon-maskable-512.png", optimize=True)
    render(180, 0.5, rounded=False).convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)
    render(48, 0.56, rounded=True).save(OUT / "favicon-48.png", optimize=True)


if __name__ == "__main__":
    main()
