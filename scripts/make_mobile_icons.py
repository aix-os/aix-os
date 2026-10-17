"""
AIX OS — генерация PNG-иконок для мобильного приложения.

Создаёт:
  mobile/flutter_app/assets/icon/icon.png             1024×1024
  mobile/flutter_app/assets/icon/icon_foreground.png  1024×1024 (с прозрачностью)
  mobile/flutter_app/assets/icon/splash.png           512×512 (прозрачный фон)

Стиль: космос + золотая A + неоновая X + молния.

Запуск:
    .venv\\Scripts\\python.exe scripts\\make_mobile_icons.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "mobile" / "flutter_app" / "assets" / "icon"
OUT.mkdir(parents=True, exist_ok=True)

# Цвета AIX OS
COSMOS = (10, 14, 39)
COSMOS2 = (19, 26, 58)
NEON = (0, 240, 255)
PURPLE = (139, 0, 255)
GOLD = (255, 215, 0)


def _font(size: int) -> ImageFont.FreeTypeFont:
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
            except Exception:
                continue
    return ImageFont.load_default()


def _radial_bg(size: int, with_bg: bool = True) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0) if not with_bg else COSMOS + (255,))
    draw = ImageDraw.Draw(img, "RGBA")
    cx = cy = size // 2

    # Фиолетовое свечение
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


def _draw_main_icon(size: int, with_bg: bool = True) -> Image.Image:
    img = _radial_bg(size, with_bg=with_bg)
    draw = ImageDraw.Draw(img, "RGBA")
    cx = cy = size // 2

    # Орбиты
    for r_frac, col, w in [(0.42, NEON, 3), (0.34, PURPLE, 2)]:
        r = int(size * r_frac)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=col + (70,), width=w)

    # Буквы A и X
    font = _font(int(size * 0.44))
    a_bbox = draw.textbbox((0, 0), "A", font=font)
    a_w = a_bbox[2] - a_bbox[0]
    a_h = a_bbox[3] - a_bbox[1]
    draw.text((cx - a_w - int(size * 0.02), cy - a_h // 2 - int(size * 0.03)),
              "A", font=font, fill=GOLD)

    x_bbox = draw.textbbox((0, 0), "X", font=font)
    x_w = x_bbox[2] - x_bbox[0]
    x_h = x_bbox[3] - x_bbox[1]
    draw.text((cx + int(size * 0.02), cy - x_h // 2 - int(size * 0.03)),
              "X", font=font, fill=NEON)

    # Молния
    s = size / 512
    pts = [
        (cx + int(10 * s), cy - int(80 * s)),
        (cx - int(18 * s), cy - int(6 * s)),
        (cx + int(10 * s), cy - int(6 * s)),
        (cx - int(14 * s), cy + int(80 * s)),
        (cx + int(30 * s), cy + int(10 * s)),
        (cx - int(2 * s), cy + int(10 * s)),
    ]
    draw.polygon(pts, fill=NEON + (240,))
    return img


def _draw_splash(size: int) -> Image.Image:
    """Splash — прозрачный фон, просто логотип."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    cx = cy = size // 2

    # Орбиты
    for r_frac, col, w in [(0.42, NEON, 3), (0.34, PURPLE, 2)]:
        r = int(size * r_frac)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=col + (120,), width=w)

    # Буквы A и X
    font = _font(int(size * 0.44))
    a_bbox = draw.textbbox((0, 0), "A", font=font)
    a_w = a_bbox[2] - a_bbox[0]
    a_h = a_bbox[3] - a_bbox[1]
    draw.text((cx - a_w - int(size * 0.02), cy - a_h // 2 - int(size * 0.03)),
              "A", font=font, fill=GOLD)

    x_bbox = draw.textbbox((0, 0), "X", font=font)
    x_w = x_bbox[2] - x_bbox[0]
    x_h = x_bbox[3] - x_bbox[1]
    draw.text((cx + int(size * 0.02), cy - x_h // 2 - int(size * 0.03)),
              "X", font=font, fill=NEON)

    # Молния
    s = size / 512
    pts = [
        (cx + int(10 * s), cy - int(80 * s)),
        (cx - int(18 * s), cy - int(6 * s)),
        (cx + int(10 * s), cy - int(6 * s)),
        (cx - int(14 * s), cy + int(80 * s)),
        (cx + int(30 * s), cy + int(10 * s)),
        (cx - int(2 * s), cy + int(10 * s)),
    ]
    draw.polygon(pts, fill=NEON + (240,))
    return img


def main() -> int:
    # 1. Основная иконка (с фоном) — 1024×1024
    icon = _draw_main_icon(1024, with_bg=True)
    icon.convert("RGB").save(OUT / "icon.png", "PNG")
    print(f"OK {OUT / 'icon.png'}")

    # 2. Foreground (без фона, прозрачность по краям) — 1024×1024
    fg = _draw_main_icon(1024, with_bg=False)
    fg.save(OUT / "icon_foreground.png", "PNG")
    print(f"OK {OUT / 'icon_foreground.png'}")

    # 3. Splash — 512×512 прозрачный
    splash = _draw_splash(512)
    splash.save(OUT / "splash.png", "PNG")
    print(f"OK {OUT / 'splash.png'}")

    print()
    print("Готово. Дальше:")
    print("  cd mobile\\flutter_app")
    print("  flutter pub run flutter_launcher_icons")
    print("  flutter pub run flutter_native_splash:create")
    return 0


if __name__ == "__main__":
    sys.exit(main())