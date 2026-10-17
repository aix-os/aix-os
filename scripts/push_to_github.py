"""Подготовка файлов ноды и автоматическая отправка на GitHub."""
import subprocess
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DEPLOY_DIR = ROOT / "hf_deploy"
GITHUB_REPO = "https://github.com/kikini-bot/aix-os-node.git"

def run(cmd, cwd=None):
    print(f"▶ {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, shell=True)
    if res.returncode != 0:
        print(f"❌ Ошибка: {' '.join(cmd)}")
        sys.exit(1)

# 1. Готовим папку hf_deploy
print("📦 Подготовка файлов ноды...")
if DEPLOY_DIR.exists():
    shutil.rmtree(DEPLOY_DIR)
DEPLOY_DIR.mkdir()

(DEPLOY_DIR / "README.md").write_text("# AIX OS Cloud Node\n\nНода для мобильного кошелька.", encoding="utf-8")

dockerfile = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD python -m network.server --host 0.0.0.0 --port $PORT --data data/chain_A.json
"""
(DEPLOY_DIR / "Dockerfile").write_text(dockerfile, encoding="utf-8")

# Копируем только нужные для сервера папки и файлы
for item in ["config.py", "requirements.txt", "core", "crypto", "network", "storage", "data"]:
    src = ROOT / item
    dst = DEPLOY_DIR / item
    if src.exists():
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

# Очищаем data от локальных кошельков и старых цепочек
data_dir = DEPLOY_DIR / "data"
if data_dir.exists():
    for p in data_dir.glob("*.json"):
        p.unlink()
    wallets_dir = data_dir / "wallets"
    if wallets_dir.exists():
        shutil.rmtree(wallets_dir)
    wallets_dir.mkdir()

# 2. Пушим на GitHub
print("\n🚀 Отправка на GitHub...")
run(["git", "init"], cwd=DEPLOY_DIR)
run(["git", "add", "."], cwd=DEPLOY_DIR)
run(["git", "commit", "-m", "Deploy AIX OS Node to Render"], cwd=DEPLOY_DIR)
run(["git", "branch", "-M", "main"], cwd=DEPLOY_DIR)
run(["git", "remote", "add", "origin", GITHUB_REPO], cwd=DEPLOY_DIR)
run(["git", "push", "-u", "origin", "main", "-f"], cwd=DEPLOY_DIR)

print("\n✅ Файлы успешно загружены на GitHub!")
print("👉 Теперь переходи на Render.com и создавай Web Service.")