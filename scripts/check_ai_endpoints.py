"""Диагностика: живы ли эндпоинты AI Memory."""
import sys
import requests

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8010"

print(f"Проверяю ноду: {URL}\n")

# 1. Нода вообще жива?
try:
    r = requests.get(f"{URL}/status", timeout=3)
    print(f"[OK]   /status            -> {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"       height={d.get('height')}")
        print(f"       ai_memory_count={d.get('ai_memory_count', 'NOT IN STATUS')}")
except Exception as e:
    print(f"[FAIL] /status           -> {e}")
    print()
    print("Нода не отвечает. Запусти её:")
    print("  .\\scripts\\run_all.ps1")
    print("или вручную:")
    print("  .\\.venv\\Scripts\\python.exe -m network.server --port 8010 --data data/chain_A.json")
    sys.exit(1)

# 2. AI Memory эндпоинты (GET)
print()
endpoints = [
    "/ai/memory",
    "/ai/memory/stats",
    "/ai/memory/latest",
    "/ai/memory/critical",
]
for path in endpoints:
    try:
        r = requests.get(f"{URL}{path}", timeout=3)
        if r.status_code == 200:
            print(f"[OK]   GET  {path}")
        else:
            print(f"[FAIL] GET  {path}  -> {r.status_code}")
    except Exception as e:
        print(f"[FAIL] GET  {path}  -> {e}")

# 3. POST /ai/remember
print()
try:
    r = requests.post(
        f"{URL}/ai/remember",
        json={
            "text": "Диагностика check_ai_endpoints.py",
            "kind": "MILESTONE",
            "priority": "NORMAL",
            "tags": ["diagnostic"],
        },
        timeout=5,
    )
    if r.status_code == 200:
        d = r.json()
        print(f"[OK]   POST /ai/remember -> id={d['id']} total={d['total']}")
        print()
        print(">>> ВСЁ РАБОТАЕТ. AI Memory вшита в API.")
    elif r.status_code == 404:
        print(f"[FAIL] POST /ai/remember -> 404 Not Found")
        print()
        print(">>> Нода работает на СТАРОМ коде.")
        print(">>> Убей все python и запусти заново:")
        print("      .\\scripts\\stop_all.ps1")
        print("      .\\scripts\\run_all.ps1")
    else:
        print(f"[FAIL] POST /ai/remember -> {r.status_code}: {r.text[:200]}")
except Exception as e:
    print(f"[FAIL] POST /ai/remember -> {e}")