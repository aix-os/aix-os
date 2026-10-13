"""
Патч web/index.html и web/landing/index.html — вставка иконок и manifest.

Идемпотентен. Бэкапы: *.icons.bak. Если якорь не найден — пропуск файла.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_web_icons.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDING = ROOT / "web" / "landing" / "index.html"
WALLET = ROOT / "web" / "index.html"

MARKER = "aix-icons"

ICONS_BLOCK_LANDING = """<!-- aix-icons -->
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="icon" type="image/x-icon" href="favicon.ico">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="manifest" href="site.webmanifest">
<meta name="theme-color" content="#0A0E27">
<!-- /aix-icons -->
"""

ICONS_BLOCK_WALLET = """<!-- aix-icons -->
<link rel="icon" type="image/svg+xml" href="/landing/favicon.svg">
<link rel="icon" type="image/x-icon" href="/landing/favicon.ico">
<link rel="apple-touch-icon" href="/landing/apple-touch-icon.png">
<meta name="theme-color" content="#0A0E27">
<!-- /aix-icons -->
"""


def _patch(path: Path, block: str) -> bool:
    if not path.exists():
        print(f"[SKIP] {path} — не найден")
        return False

    src = path.read_text(encoding="utf-8")
    if MARKER in src:
        print(f"[SKIP] {path} — уже пропатчен")
        return True

    # Якорь: <meta charset="UTF-8"> или <title> или <head>
    anchors = [
        '<meta charset="UTF-8">',
        "<meta charset='UTF-8'>",
        '<meta charset="utf-8">',
        "<title>",
    ]
    hit = None
    for a in anchors:
        if a in src:
            hit = a
            break

    if hit is None:
        print(f"[FATAL] {path} — не найден якорь (<meta charset> или <title>)")
        return False

    bak = path.with_suffix(path.suffix + ".icons.bak")
    bak.write_bytes(path.read_bytes())
    print(f"[{path.name}] backup -> {bak.name}")

    src = src.replace(hit, hit + "\n" + block, 1)
    path.write_text(src, encoding="utf-8")
    print(f"[{path.name}] OK: иконки + manifest вставлены")
    return True


def main() -> int:
    ok_landing = _patch(LANDING, ICONS_BLOCK_LANDING)
    ok_wallet = _patch(WALLET, ICONS_BLOCK_WALLET)
    if ok_landing or ok_wallet:
        print()
        print("✅ Патч иконок завершён.")
        print("   Обнови страницу в браузере: Ctrl+F5")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())