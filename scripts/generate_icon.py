"""Génère l'icône de l'application (assets/icon.png + assets/icon.ico).

Un script plutôt qu'un fichier binaire versionné à la main : si la
charte visuelle change (`desktop/theme.py`), l'icône peut être
régénérée à l'identique avec `python scripts/generate_icon.py`.

Produit un PNG 1024×1024 (source pour la conversion .icns sur Mac, voir
scripts/build_macos.sh) et un .ico multi-résolutions pour Windows.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = "#C6491F"
MARK = "#FFF7F2"

SIZE = 1024
SUPERSAMPLE = 4


def build_icon() -> Image.Image:
    canvas_size = SIZE * SUPERSAMPLE
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    radius = int(canvas_size * 0.24)
    draw.rounded_rectangle(
        [(0, 0), (canvas_size - 1, canvas_size - 1)],
        radius=radius,
        fill=ACCENT,
    )

    # Triangle de lecture ("reel"), centré.
    cx, cy = canvas_size / 2, canvas_size / 2
    tri_half = canvas_size * 0.19
    triangle = [
        (cx - tri_half * 0.72, cy - tri_half),
        (cx + tri_half * 0.95, cy),
        (cx - tri_half * 0.72, cy + tri_half),
    ]
    draw = ImageDraw.Draw(image)
    draw.polygon(triangle, fill=MARK)

    return image.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> None:
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(exist_ok=True)

    icon = build_icon()
    png_path = assets_dir / "icon.png"
    icon.save(png_path)

    ico_path = assets_dir / "icon.ico"
    icon.save(
        ico_path,
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    print(f"Écrit : {png_path}")
    print(f"Écrit : {ico_path}")


if __name__ == "__main__":
    main()
