"""
Замена GitHub URL во всех файлах проекта.

Использование:
    .venv\\Scripts\\python.exe scripts\\patch_github_url.py <from> <to>

Примеры:
    patch_github_url.py kikini-bot aix-os
    patch_github_url.py ТВОЙ_ЛОГИН aix-os
    patch_github_url.py YOUR_USERNAME aix-os

Заменяет строку <from> на <to> ТОЛЬКО в контексте github.com,
чтобы случайно не тронуть другие упоминания.

Файлы:
    web/landing/index.html
    web/landing/roadmap.html
    README.md
    docs/HABR_ARTICLE.md
    docs/POST_VK_TELEGRAM.md
    docs/POST_HN_REDDIT.md
    docs/RELEASE.md

Бэкап: *.url.bak
Идемпотентен.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS = [
    ROOT / "web" / "landing" / "index.html",
    ROOT / "web" / "landing" / "roadmap.html",
    ROOT / "README.md",
    ROOT / "docs" / "HABR_ARTICLE.md",
    ROOT / "docs" / "POST_VK_TELEGRAM.md",
    ROOT / "docs" / "POST_HN_REDDIT.md",
    ROOT / "docs" / "RELEASE.md",
]


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: patch_github_url.py <from> <to>")
        print("Examples:")
        print("  patch_github_url.py kikini-bot aix-os")
        print("  patch_github_url.py ТВОЙ_ЛОГИН aix-os")
        print("  patch_github_url.py YOUR_USERNAME aix-os")
        return 1

    src_name = sys.argv[1].strip().lstrip("@")
    dst_name = sys.argv[2].strip().lstrip("@")

    if not src_name or not dst_name:
        print("[FATAL] Пустой аргумент")
        return 1

    if src_name == dst_name:
        print(f"[SKIP] from == to == '{src_name}'")
        return 0

    # Заменяем ТОЛЬКО в контексте github.com/<name>
    from_a = f"github.com/{src_name}"
    to_a = f"github.com/{dst_name}"

    print(f"Заменяю '{from_a}' -> '{to_a}'")
    print()

    total_files = 0
    total_replacements = 0

    for path in TARGETS:
        if not path.exists():
            print(f"[SKIP] {path.relative_to(ROOT)} — нет файла")
            continue

        text = path.read_text(encoding="utf-8")
        n = text.count(from_a)
        if n == 0:
            print(f"[SKIP] {path.relative_to(ROOT)} — нет вхождений")
            continue

        bak = path.with_suffix(path.suffix + ".url.bak")
        bak.write_bytes(path.read_bytes())

        new_text = text.replace(from_a, to_a)
        path.write_text(new_text, encoding="utf-8")

        total_files += 1
        total_replacements += n
        print(f"[{path.relative_to(ROOT)}] OK: {n} замен (backup -> {bak.name})")

    print()
    if total_files == 0:
        print("Нечего заменять.")
        return 1

    print(f"OK. Файлов изменено: {total_files}, замен всего: {total_replacements}")
    print()
    print("Проверь:")
    print("   Select-String -Path web\\landing\\*.html,README.md -Pattern 'github.com'")
    return 0


if __name__ == "__main__":
    sys.exit(main())