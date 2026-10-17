"""Сборка AIX OS для Windows через виртуальный диск (обход кириллицы)."""
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
DRIVE = "R:"
FLUTTER_DIR = f"{DRIVE}\\mobile\\flutter_app"
PUB_CACHE_DIR = f"{DRIVE}\\pub_cache"

def run_cmd(cmd, cwd=None, env=None):
    print(f"▶ {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=cwd, shell=True, env=env)
    if res.returncode != 0:
        print(f"❌ Ошибка выполнения: {cmd}")
        sys.exit(1)

def main():
    print("===========================================")
    print("  AIX OS — Сборка Windows EXE")
    print("===========================================\n")

    print("[1/4] Создание виртуального диска R:...")
    subprocess.run(["subst", DRIVE, "/d"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run_cmd(["subst", DRIVE, str(ROOT)])

    env = os.environ.copy()
    env["PUB_CACHE"] = PUB_CACHE_DIR

    print("\n[2/4] Очистка Flutter...")
    run_cmd(["flutter", "clean"], cwd=FLUTTER_DIR, env=env)

    print("\n[3/4] Загрузка зависимостей...")
    run_cmd(["flutter", "pub", "get"], cwd=FLUTTER_DIR, env=env)

    print("\n[4/4] Сборка Windows...")
    run_cmd(["flutter", "build", "windows", "--release"], cwd=FLUTTER_DIR, env=env)

    print("\nЗавершение...")
    subprocess.run(["subst", DRIVE, "/d"], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("\n===========================================")
    print("  🎉 ГОТОВО! EXE лежит здесь:")
    print(f"  {ROOT}\\mobile\\flutter_app\\build\\windows\\x64\\runner\\Release\\")
    print("===========================================")

if __name__ == "__main__":
    main()