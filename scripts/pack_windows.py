"""Упаковка Windows-версии в ZIP для GitHub."""
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
RELEASE_DIR = ROOT / "mobile" / "flutter_app" / "build" / "windows" / "x64" / "runner" / "Release"
OUTPUT_ZIP = ROOT / "aix_os_windows.zip"

if not RELEASE_DIR.exists():
    print("❌ Папка Release не найдена. Сначала собери Windows.")
    exit(1)

print("📦 Упаковка Windows-версии...")
shutil.make_archive(str(OUTPUT_ZIP.with_suffix('')), 'zip', RELEASE_DIR)
print(f"✅ Готово! Архив лежит здесь: {OUTPUT_ZIP}")