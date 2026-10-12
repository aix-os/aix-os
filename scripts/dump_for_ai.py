"""AIX OS — сборка всех исходников в один файл для AI-ассистента."""
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.resolve()
OUTPUT = ROOT / "AIX_OS_FULL_DUMP.txt"

INCLUDE_EXT = {
    ".py", ".md", ".html", ".js", ".css", ".json",
    ".yaml", ".yml", ".toml", ".txt", ".dart",
    ".ps1", ".sh", ".bat", ".cfg", ".ini",
    ".rs", ".go", ".java", ".kt", ".swift",
    ".sql", ".gitignore", ".gitattributes",
}

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "env", "__pycache__",
    "node_modules", ".dart_tool", "build", "dist",
    ".idea", ".vscode", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "site-packages", "web_backup",
    "target", ".gradle", ".flutter-plugins",
}

EXCLUDE_FILE_PATTERNS = [
    ".wallet.json", ".pyc", ".pyo", ".pyd", ".dll", ".exe",
    ".so", ".dylib", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".svg", ".pdf", ".zip", ".tar", ".gz", ".7z", ".db",
    ".sqlite", ".lock", ".backup", ".bak",
    "AIX_OS_FULL_DUMP.txt",
]

EXCLUDE_DIR_PREFIXES = ("data_backup_",)


def is_excluded(path: Path) -> bool:
    name = path.name
    for p in EXCLUDE_FILE_PATTERNS:
        if name.endswith(p):
            return True
    for parent in path.parents:
        if parent.name in EXCLUDE_DIRS:
            return True
        if parent.name.startswith(EXCLUDE_DIR_PREFIXES):
            return True
    return False


def collect_files():
    files = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if is_excluded(path):
            continue
        if path.suffix.lower() in INCLUDE_EXT or path.name in (".gitignore", ".gitattributes"):
            files.append(path)
    return sorted(files)


def main():
    print(f"🔍 Сканирую {ROOT}...")
    files = collect_files()
    print(f"📄 Найдено файлов: {len(files)}")

    total_lines = 0
    total_bytes = 0

    with open(OUTPUT, "w", encoding="utf-8") as out:
        out.write("=" * 80 + "\n")
        out.write("AIX OS — FULL PROJECT DUMP\n")
        out.write(f"Сгенерировано: {datetime.now().isoformat()}\n")
        out.write(f"Корень: {ROOT}\n")
        out.write(f"Файлов: {len(files)}\n")
        out.write("=" * 80 + "\n\n")

        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                content = f"<<ОШИБКА ЧТЕНИЯ: {e}>>"

            lines = content.count("\n") + 1
            size = len(content.encode("utf-8"))
            total_lines += lines
            total_bytes += size

            out.write("\n" + "=" * 80 + "\n")
            out.write(f"📄 FILE: {rel}\n")
            out.write(f"📊 Size: {size} bytes | Lines: {lines}\n")
            out.write("=" * 80 + "\n")
            out.write(content)
            out.write("\n")

        out.write("\n" + "=" * 80 + "\n")
        out.write("КОНЕЦ ДАМПА\n")
        out.write(f"Файлов: {len(files)}\n")
        out.write(f"Всего строк: {total_lines}\n")
        out.write(f"Всего байт: {total_bytes}\n")
        out.write("=" * 80 + "\n")

    size_kb = OUTPUT.stat().st_size / 1024
    print()
    print("✅ Готово!")
    print(f"📦 Файл: {OUTPUT}")
    print(f"📊 Размер: {size_kb:.1f} KB")
    print(f"📝 Строк: {total_lines}")
    print(f"📄 Исходных файлов: {len(files)}")
    print()
    print("Скинь этот файл AI-ассистенту. Он увидит весь проект.")


if __name__ == "__main__":
    main()