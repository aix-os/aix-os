"""Подготовка файлов для деплоя ноды на Render."""
from pathlib import Path
import shutil

ROOT = Path(__file__).parent.parent
DEPLOY_DIR = ROOT / "hf_deploy"

if DEPLOY_DIR.exists():
    shutil.rmtree(DEPLOY_DIR)
DEPLOY_DIR.mkdir()

# 1. Создаем README.md
(DEPLOY_DIR / "README.md").write_text("# AIX OS Cloud Node\n\nНода для мобильного кошелька.", encoding="utf-8")

# 2. Создаем Dockerfile специально под Render (использует $PORT)
dockerfile = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render передает свой порт через переменную $PORT
CMD python -m network.server --host 0.0.0.0 --port $PORT --data data/chain_A.json
"""
(DEPLOY_DIR / "Dockerfile").write_text(dockerfile, encoding="utf-8")

# 3. Копируем файлы
print("📦 Копируем файлы ноды...")
for item in ["config.py", "requirements.txt", "core", "crypto", "network", "storage", "data"]:
    src = ROOT / item
    dst = DEPLOY_DIR / item
    if src.exists():
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

# 4. Очищаем data (чтобы не загружать твои личные данные на сервер)
data_dir = DEPLOY_DIR / "data"
if data_dir.exists():
    for p in data_dir.glob("*.json"):
        p.unlink()
    wallets_dir = data_dir / "wallets"
    if wallets_dir.exists():
        shutil.rmtree(wallets_dir)
    wallets_dir.mkdir()

print("✅ Папка hf_deploy создана по пути:", DEPLOY_DIR)
print("👉 Теперь зайди на Render.com (инструкция ниже).")