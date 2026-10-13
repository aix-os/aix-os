"""
AIX OS -- промо-ролик 30 секунд, рисуется полностью в Python.

Сцены:
  0-4s   Космос: звёзды, медленный дрейф
  4-8s   Планета + орбита с точкой
  8-12s  Слоган: "Что если ОС тебя слышит?"
  12-20s Терминал с диалогом Brain
  20-24s Монеты AIX, разлетающиеся из центра
  24-28s Логотип AIX + 12 протоколов по кругу
  28-30s Финал: "Империя начинается с тебя" + URL

Запуск:
    .venv\\Scripts\\python.exe scripts\\make_promo.py

Выход:
    docs/promo.mp4
    docs/promo_poster.png   (первый кадр — постер)
"""

from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


# ---------- Константы ----------

W, H = 1280, 720
FPS = 30
DURATION = 30.0
TOTAL_FRAMES = int(FPS * DURATION)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs"
OUT_DIR.mkdir(exist_ok=True)
OUT_MP4 = OUT_DIR / "promo.mp4"
OUT_POSTER = OUT_DIR / "promo_poster.png"

# Цвета (те же что в Web UI)
COSMOS = (10, 14, 39)
COSMOS2 = (19, 26, 58)
NEON = (0, 240, 255)
PURPLE = (139, 0, 255)
GOLD = (255, 215, 0)
GREEN = (0, 255, 136)
TEXT = (224, 232, 255)
MUTED = (107, 124, 168)
RED = (255, 51, 102)


# ---------- Шрифты ----------

def _font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    """Подобрать системный шрифт под Windows/Linux/Mac."""
    windir = os.environ.get("WINDIR", r"C:\Windows")
    if mono:
        candidates = [
            os.path.join(windir, "Fonts", "consola.ttf"),
            os.path.join(windir, "Fonts", "lucon.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/System/Library/Fonts/Menlo.ttc",
        ]
    else:
        if bold:
            candidates = [
                os.path.join(windir, "Fonts", "segoeuib.ttf"),
                os.path.join(windir, "Fonts", "arialbd.ttf"),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
        else:
            candidates = [
                os.path.join(windir, "Fonts", "segoeui.ttf"),
                os.path.join(windir, "Fonts", "arial.ttf"),
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
            ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


# ---------- Утилиты ----------

def _ease(t: float) -> float:
    """Плавная S-кривая [0..1]."""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _lerp(a, b, t: float):
    return a + (b - a) * t


def _color_lerp(c1, c2, t):
    return tuple(int(_lerp(c1[i], c2[i], t)) for i in range(3))


def _text_size(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_text_center(
    draw: ImageDraw.ImageDraw,
    text: str,
    font,
    color,
    cx: int,
    cy: int,
    letter_spacing: int = 0,
):
    """Нарисовать текст с центровкой и опциональным letter-spacing."""
    if letter_spacing == 0:
        w, h = _text_size(draw, text, font)
        draw.text((cx - w // 2, cy - h // 2), text, font=font, fill=color)
        return
    # с letter-spacing
    widths = []
    for ch in text:
        bbox = draw.textbbox((0, 0), ch, font=font)
        widths.append(bbox[2] - bbox[0])
    total = sum(widths) + letter_spacing * (len(text) - 1)
    x = cx - total // 2
    for ch, w_ch in zip(text, widths):
        draw.text((x, cy), ch, font=font, fill=color, anchor="lm")
        x += w_ch + letter_spacing


def _draw_bg_cosmos(frame: Image.Image, t: float, seed: int = 42):
    """Тёмный космос с тонким радиальным градиентом и лёгким дрейфом."""
    rng = random.Random(seed)
    base = Image.new("RGB", (W, H), COSMOS)
    draw = ImageDraw.Draw(base, "RGBA")

    # Пульсирующее свечение (два радиальных)
    pulse = 0.5 + 0.5 * math.sin(t * 0.6)
    cx, cy = int(W * 0.20), int(H * 0.25)
    r = 380 + int(pulse * 30)
    for i in range(12, 0, -1):
        rr = r * i // 12
        alpha = int(30 * (12 - i) / 12)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                     fill=(139, 0, 255, alpha))

    cx2, cy2 = int(W * 0.82), int(H * 0.80)
    r2 = 340 + int((1 - pulse) * 40)
    for i in range(12, 0, -1):
        rr = r2 * i // 12
        alpha = int(24 * (12 - i) / 12)
        draw.ellipse([cx2 - rr, cy2 - rr, cx2 + rr, cy2 + rr],
                     fill=(0, 240, 255, alpha))

    # Звёзды (дрейфуют влево-вверх)
    stars = [(rng.randint(0, W), rng.randint(0, H),
              rng.uniform(0.5, 1.5), rng.uniform(0.3, 1.0))
             for _ in range(180)]
    for (sx, sy, sr, twinkle) in stars:
        drift_x = int((sx - t * 6) % W)
        drift_y = int((sy - t * 3) % H)
        alpha = int(200 * twinkle * (0.6 + 0.4 * math.sin(t * 2 + sx)))
        col = (255, 255, 255, max(30, min(255, alpha)))
        draw.ellipse([drift_x - sr, drift_y - sr, drift_x + sr, drift_y + sr],
                     fill=col)

    frame.paste(base, (0, 0))


# ---------- Сцены ----------

def scene_cosmos(t: float) -> Image.Image:
    """0-4s: чистый космос с лёгким дрейфом."""
    img = Image.new("RGB", (W, H), COSMOS)
    _draw_bg_cosmos(img, t)
    draw = ImageDraw.Draw(img, "RGBA")

    # Плавное появление заголовка AIX OS к концу сцены
    if t > 1.5:
        alpha = _ease((t - 1.5) / 1.5)
        col = (255, 215, 0, int(255 * alpha))
        font = _font(72, bold=True)
        _draw_text_center(draw, "AIX", font, col, W // 2 - 60, H // 2, letter_spacing=8)
        col2 = (0, 240, 255, int(255 * alpha))
        _draw_text_center(draw, "OS", font, col2, W // 2 + 80, H // 2, letter_spacing=8)
        # Молния
        _draw_lightning(draw, W // 2 + 10, H // 2, int(255 * alpha))

    return img


def _draw_lightning(draw: ImageDraw.ImageDraw, cx: int, cy: int, alpha: int):
    """Простая молния ⚡ между буквами."""
    pts = [
        (cx - 12, cy - 28), (cx + 8, cy - 28), (cx - 4, cy - 4),
        (cx + 12, cy - 4), (cx - 10, cy + 28), (cx + 4, cy + 4),
        (cx - 12, cy + 4),
    ]
    col = (0, 240, 255, alpha)
    draw.polygon(pts, fill=col)


def scene_planet(t: float) -> Image.Image:
    """4-8s: планета с орбитой и точкой."""
    img = Image.new("RGB", (W, H), COSMOS)
    _draw_bg_cosmos(img, t + 4)
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = W // 2, H // 2
    # Планета: круглая, градиент от сине-фиолетового к тёмному
    R = 170
    # Внешнее свечение
    for i in range(20, 0, -1):
        rr = R + i * 4
        alpha = int(20 * i / 20)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                     fill=(139, 0, 255, alpha))
    # Сама планета: несколько кругов с уменьшающейся яркостью
    for i in range(20, 0, -1):
        rr = R * i // 20
        color = _color_lerp(COSMOS2, PURPLE, i / 20)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color)
    # Блик сверху
    draw.ellipse([cx - 90, cy - 130, cx + 20, cy - 40],
                 fill=(200, 220, 255, 60))

    # Орбита — эллипс
    orbit_rx, orbit_ry = 320, 110
    draw.ellipse([cx - orbit_rx, cy - orbit_ry, cx + orbit_rx, cy + orbit_ry],
                 outline=(0, 240, 255, 120), width=2)

    # Точка на орбите движется
    angle = t * 1.8
    px = cx + int(orbit_rx * math.cos(angle))
    py = cy + int(orbit_ry * math.sin(angle))
    for i in range(6, 0, -1):
        rr = i * 3
        alpha = int(60 + 195 * (1 - i / 6))
        draw.ellipse([px - rr, py - rr, px + rr, py + rr],
                     fill=(0, 240, 255, alpha))
    draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(255, 255, 255))

    return img


def scene_tagline(t: float) -> Image.Image:
    """8-12s: слоган 'Что если ОС тебя слышит?'."""
    img = Image.new("RGB", (W, H), COSMOS)
    _draw_bg_cosmos(img, t + 8)
    draw = ImageDraw.Draw(img, "RGBA")

    # Появление текста с alpha-ramp
    appear = _ease(min(1.0, t / 1.2))
    fade_in = int(255 * appear)

    font_big = _font(58, bold=True)
    font_small = _font(28, bold=False)

    # Основной слоган
    _draw_text_center(draw, "Что если", font_big, (224, 232, 255, fade_in), W // 2, H // 2 - 80)
    _draw_text_center(draw, "ОС тебя слышит?", font_big,
                      (0, 240, 255, fade_in), W // 2, H // 2 + 5)

    # Подпись снизу появляется с задержкой
    if t > 1.8:
        a2 = _ease((t - 1.8) / 1.2)
        _draw_text_center(draw, "Не кнопки. Не формы. Слова.",
                          font_small, (107, 124, 168, int(255 * a2)),
                          W // 2, H // 2 + 110)

    return img


def scene_terminal(t: float) -> Image.Image:
    """12-20s: имитация терминала с диалогом."""
    img = Image.new("RGB", (W, H), COSMOS)
    _draw_bg_cosmos(img, t + 12)
    draw = ImageDraw.Draw(img, "RGBA")

    # Окно терминала
    box_w, box_h = 1020, 500
    bx1, by1 = (W - box_w) // 2, (H - box_h) // 2
    bx2, by2 = bx1 + box_w, by1 + box_h

    # Тень + рамка
    draw.rectangle([bx1 + 8, by1 + 8, bx2 + 8, by2 + 8], fill=(0, 0, 0, 120))
    draw.rectangle([bx1, by1, bx2, by2], fill=(5, 8, 26), outline=(0, 240, 255, 180), width=2)

    # Заголовок окна
    draw.rectangle([bx1, by1, bx2, by1 + 34], fill=(19, 26, 58))
    draw.text((bx1 + 16, by1 + 9), "AIX OS -- brain chat --wallet alice",
              font=_font(14, mono=True), fill=(107, 124, 168))

    # Три кружка (кнопки)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cxx = bx2 - 84 + i * 22
        draw.ellipse([cxx, by1 + 12, cxx + 10, by1 + 22], fill=col)

    # Содержимое: строки появляются по одной
    lines = [
        ("вы> ", "какая высота цепочки?", 0.6, (0, 240, 255)),
        ("🧠 ", "думаю...  [chain_status]", 1.8, (107, 124, 168)),
        ("🧠 ", "Высота цепочки AIX OS -- 17 блоков.", 3.4, (224, 232, 255)),
        ("вы> ", "отправь 1 AIX bob", 4.6, (0, 240, 255)),
        ("🧠 ", "думаю...  [safe_send]", 5.6, (107, 124, 168)),
        ("", "┌── ПОДТВЕРЖДЕНИЕ ──────────", 6.4, (107, 124, 168)),
        ("", "│ Сумма:  1.0 AIX", 6.8, (107, 124, 168)),
        ("", "│ Баланс: 200.0 → 199.0 AIX", 7.2, (107, 124, 168)),
        ("", "└───────────────────────────", 7.6, (107, 124, 168)),
        ("", "Отправить? [y/N] y", 7.9, (255, 215, 0)),
        ("🧠 ", "Отправлено. TX: dec9b1b3... (broadcast to 1 peer)", 8.2, (0, 255, 136)),
    ]

    font_mono = _font(18, mono=True)
    y = by1 + 56
    line_h = 30
    for (prefix, text, appear_at, color) in lines:
        if t < appear_at:
            break
        # первая буква за раз
        age = t - appear_at
        chars_visible = min(len(text), int(age * 60) + 1)
        visible = text[:chars_visible]
        # Префикс
        if prefix:
            draw.text((bx1 + 24, y), prefix, font=font_mono, fill=(107, 124, 168))
        pw, _ = _text_size(draw, prefix, font_mono)
        draw.text((bx1 + 24 + pw, y), visible, font=font_mono, fill=color)
        y += line_h

    return img


def scene_coins(t: float) -> Image.Image:
    """20-24s: монеты AIX разлетаются из центра."""
    img = Image.new("RGB", (W, H), COSMOS)
    _draw_bg_cosmos(img, t + 20)
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = W // 2, H // 2
    rng = random.Random(7)
    for i in range(24):
        angle = rng.uniform(0, 2 * math.pi)
        speed = rng.uniform(100, 360)
        size = rng.randint(22, 40)
        # Прогресс — от 0 до 1 за 4 секунды
        p = _ease(min(1.0, t / 3.5))
        dist = speed * p
        px = int(cx + dist * math.cos(angle))
        py = int(cy + dist * math.sin(angle))
        alpha = int(255 * (1 - p * 0.85))

        # Монета: круг + свечение
        for j in range(4, 0, -1):
            rr = size // 2 + j * 3
            draw.ellipse([px - rr, py - rr, px + rr, py + rr],
                         fill=(255, 215, 0, alpha // 6))
        draw.ellipse([px - size // 2, py - size // 2,
                      px + size // 2, py + size // 2],
                     fill=(255, 215, 0, alpha),
                     outline=(180, 140, 0, alpha), width=2)
        # Символ $ / AIX
        f = _font(int(size * 0.55), bold=True)
        w_ch, h_ch = _text_size(draw, "A", f)
        draw.text((px - w_ch // 2, py - h_ch // 2 - 1), "A",
                  font=f, fill=(90, 60, 0, alpha))

    # Текст
    appear = _ease(min(1.0, max(0.0, (t - 1.0) / 1.0)))
    f = _font(46, bold=True)
    _draw_text_center(draw, "21 000 000 AIX", f,
                      (255, 215, 0, int(255 * appear)), W // 2, H // 2 + 220)

    return img


def scene_logo(t: float) -> Image.Image:
    """24-28s: логотип AIX ⚡ OS + 12 протоколов по кругу."""
    img = Image.new("RGB", (W, H), COSMOS)
    _draw_bg_cosmos(img, t + 24)
    draw = ImageDraw.Draw(img, "RGBA")

    cx, cy = W // 2, H // 2

    # Логотип по центру
    f = _font(80, bold=True)
    _draw_text_center(draw, "AIX", f, GOLD, cx - 80, cy, letter_spacing=6)
    _draw_text_center(draw, "OS", f, NEON, cx + 85, cy, letter_spacing=6)
    _draw_lightning(draw, cx + 10, cy, 255)

    # 12 протоколов по кругу — каждый появляется в свой момент
    protocols = [
        ("🎁", "Gift"), ("🕰", "TimeLock"), ("🏅", "SBT"),
        ("🎰", "Lottery"), ("🎗", "DMS"), ("🪪", "AIX-ID"),
        ("🔥", "Burn"), ("📇", "Contacts"), ("💱", "Swap"),
        ("🧬", "PoC"), ("🔄", "Sync"), ("🧠", "Brain"),
    ]
    R = 240
    f_small = _font(15, bold=True)
    for i, (emoji, name) in enumerate(protocols):
        appear_at = 0.4 + i * 0.18
        if t < appear_at:
            continue
        a = _ease(min(1.0, (t - appear_at) / 0.5))
        angle = -math.pi / 2 + 2 * math.pi * i / 12
        px = int(cx + R * math.cos(angle))
        py = int(cy + R * math.sin(angle))
        # Точка
        r = int(16 * a)
        alpha = int(255 * a)
        for j in range(6, 0, -1):
            rr = r + j * 2
            draw.ellipse([px - rr, py - rr, px + rr, py + rr],
                         fill=(139, 0, 255, alpha // 4))
        draw.ellipse([px - r, py - r, px + r, py + r],
                     fill=(19, 26, 58, alpha),
                     outline=(0, 240, 255, alpha), width=2)
        # Текст под точкой
        w_t, h_t = _text_size(draw, name, f_small)
        draw.text((px - w_t // 2, py + r + 6), name, font=f_small,
                  fill=(224, 232, 255, alpha))

    return img


def scene_final(t: float) -> Image.Image:
    """28-30s: финал."""
    img = Image.new("RGB", (W, H), COSMOS)
    _draw_bg_cosmos(img, t + 28)
    draw = ImageDraw.Draw(img, "RGBA")

    # Финальный заголовок
    appear = _ease(min(1.0, t / 1.0))
    fade = int(255 * appear)

    f_big = _font(52, bold=True)
    _draw_text_center(draw, "Империя начинается", f_big,
                      (255, 215, 0, fade), W // 2, H // 2 - 60)
    _draw_text_center(draw, "с тебя.", f_big,
                      (0, 240, 255, fade), W // 2, H // 2 + 10)

    if t > 0.8:
        a2 = _ease((t - 0.8) / 0.7)
        f_small = _font(22, bold=True)
        _draw_text_center(draw, "AIX OS -- Operating System for Life",
                          f_small, (107, 124, 168, int(255 * a2)),
                          W // 2, H // 2 + 110)

    if t > 1.4:
        a3 = _ease((t - 1.4) / 0.6)
        f_link = _font(18, mono=True)
        _draw_text_center(draw, "aix-os.local  |  github.com/aix-os",
                          f_link, (0, 240, 255, int(255 * a3)),
                          W // 2, H - 60)

    return img


# ---------- Рендер ----------

SCENES = [
    (0.0, 4.0, scene_cosmos),
    (4.0, 4.0, scene_planet),
    (8.0, 4.0, scene_tagline),
    (12.0, 8.0, scene_terminal),
    (20.0, 4.0, scene_coins),
    (24.0, 4.0, scene_logo),
    (28.0, 2.0, scene_final),
]


def render_frame(frame_idx: int) -> Image.Image:
    t = frame_idx / FPS
    for start, dur, fn in SCENES:
        if start <= t < start + dur:
            return fn(t - start)
    return scene_final(dur := 2.0)


def main() -> int:
    print(f"Rendering {TOTAL_FRAMES} frames ({DURATION}s @ {FPS}fps) -> {OUT_MP4}")
    writer = imageio.get_writer(
        str(OUT_MP4),
        fps=FPS,
        codec="libx264",
        quality=8,
        pixelformat="yuv420p",
        macro_block_size=8,
    )
    poster_saved = False
    try:
        for i in range(TOTAL_FRAMES):
            frame = render_frame(i)
            writer.append_data(np.asarray(frame))
            if not poster_saved:
                frame.save(OUT_POSTER, "PNG")
                poster_saved = True
            if i % FPS == 0:
                pct = int(100 * i / TOTAL_FRAMES)
                print(f"  {pct:3d}%  t={i / FPS:5.1f}s")
    finally:
        writer.close()

    size_mb = OUT_MP4.stat().st_size / 1e6
    print()
    print(f"OK -> {OUT_MP4}")
    print(f"     {size_mb:.2f} MB, {W}x{H}, {DURATION:.0f}s")
    print(f"     poster: {OUT_POSTER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())