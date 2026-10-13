"""
Генерация иконок проекта: PNG для PWA + favicon.ico.

Рисует иконку AIX ⚡ OS напрямую через Pillow (без внешних зависимостей).

Запуск:
    .venv\\Scripts\\python.exe scripts\\make_icons.py

Выход:
    web/landing/icon-192.png
    web/landing/icon-512.png
    web/landing/apple-touch-icon.png  (180x180)
    web/landing/favicon.ico           (16, 32, 48, 64)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "landing"
OUT.mkdir(parents=True, exist_ok=True)

COSMOS = (10, 14, 39)
COSMOS2 = (19, 26, 58)
NEON = (0, 240, 255)
PURPLE = (139, 0, 255)
GOLD = (255, 215, 0)


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    windir = os.environ.get("WINDIR", r"C:\Windows")
    candidates = [
        os.path.join(windir, "Fonts", "segoeuib.ttf"),
        os.path.join(windir, "Fonts", "arialbd.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _radial_bg(size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), COSMOS)
    draw = ImageDraw.Draw(img, "RGBA")
    cx = cy = size // 2
    # Пульсирующее свечение фиолетовое
    for i in range(20, 0, -1):
        rr = int(size * 0.55 * i / 20)
        alpha = int(16 * (20 - i) / 20)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                     fill=(139, 0, 255, alpha))
    # Синее свечение снизу
    for i in range(20, 0, -1):
        rr = int(size * 0.42 * i / 20)
        alpha = int(12 * (20 - i) / 20)
        draw.ellipse([cx - rr, cy + size // 8 - rr, cx + rr, cy + size // 8 + rr],
                     fill=(0, 240, 255, alpha))
    return img


def _draw_icon(size: int) -> Image.Image:
    img = _radial_bg(size)
    draw = ImageDraw.Draw(img, "RGBA")
    cx = cy = size // 2

    # Круглые орбиты
    for r_frac, col, w in [(0.42, NEON, 2), (0.34, PURPLE, 1)]:
        r = int(size * r_frac)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (60,), width=w)

    # Буквы A и X — по бокам
    font = _font(int(size * 0.44), bold=True)
    # A (золото)
    a_bbox = draw.textbbox((0, 0), "A", font=font)
    a_w = a_bbox[2] - a_bbox[0]
    a_h = a_bbox[3] - a_bbox[1]
    draw.text((cx - a_w - int(size * 0.02), cy - a_h // 2 - int(size * 0.03)),
              "A", font=font, fill=GOLD)
    # X (неон)
    x_bbox = draw.textbbox((0, 0), "X", font=font)
    x_w = x_bbox[2] - x_bbox[0]
    x_h = x_bbox[3] - x_bbox[1]
    draw.text((cx + int(size * 0.02), cy - x_h // 2 - int(size * 0.03)),
              "X", font=font, fill=NEON)

    # Молния между ними
    s = size / 512
    pts = [
        (cx + int(10 * s), cy - int(80 * s)),
        (cx - int(18 * s), cy - int(6 * s)),
        (cx + int(10 * s), cy - int(6 * s)),
        (cx - int(14 * s), cy + int(80 * s)),
        (cx + int(30 * s), cy + int(10 * s)),
        (cx - int(2 * s), cy + int(10 * s)),
    ]
    draw.polygon(pts, fill=NEON + (230,))
    return img


def main() -> int:
    sizes = {
        "icon-192.png": 192,
        "icon-512.png": 512,
        "apple-touch-icon.png": 180,
    }
    for name, size in sizes.items():
        icon = _draw_icon(size)
        path = OUT / name
        icon.save(path, "PNG")
        print(f"OK {path.relative_to(ROOT)} ({size}x{size})")

    # favicon.ico с несколькими размерами
    ico_path = OUT / "favicon.ico"
    base = _draw_icon(256)
    base.save(ico_path, "ICO",
              sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"OK {ico_path.relative_to(ROOT)} (multi-size)")

    return 0


if __name__ == "__main__":
    sys.exit(main())