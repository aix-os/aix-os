from pathlib import Path
import json, shutil, sys

ROOT = Path(".")

# ---- 1. run_all.ps1: add --url http://127.0.0.1:PORT ----
ra = ROOT / "scripts" / "run_all.ps1"
src = ra.read_text(encoding="utf-8")
if "127.0.0.1:8010" in src:
    print("[SKIP] run_all.ps1 already patched")
else:
    shutil.copy2(ra, ra.with_suffix(".ps1.bak"))
    for port in (8010, 8011):
        old = f"--port {port} --data"
        new = f"--port {port} --url http://127.0.0.1:{port} --data"
        if src.count(old) != 1:
            print(f"[FAIL] run_all.ps1: '{old}' x{src.count(old)}"); sys.exit(1)
        src = src.replace(old, new, 1)
    ra.write_text(src, encoding="utf-8")
    print("[OK] run_all.ps1: --url 127.0.0.1 added")

# ---- 2. peers files: rewrite localhost -> 127.0.0.1 ----
for port, peer in [(8010, 8011), (8011, 8010)]:
    pf = ROOT / "data" / f"peers_{port}.json"
    if not pf.exists():
        print(f"[WARN] {pf} not found")
        continue
    data = json.loads(pf.read_text(encoding="utf-8"))
    fixed = [u.replace("localhost", "127.0.0.1") for u in data.get("peers", [])]
    data["peers"] = fixed
    shutil.copy2(pf, pf.with_suffix(".json.bak"))
    pf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {pf.name} -> {fixed}")

# ---- 3. web/index.html: default NODE_URL ----
wh = ROOT / "web" / "index.html"
wsrc = wh.read_text(encoding="utf-8")
if 'NODE_URL = "http://127.0.0.1:8010"' in wsrc:
    print("[SKIP] web/index.html already patched")
else:
    shutil.copy2(wh, wh.with_suffix(".html.bak4"))
    wsrc = wsrc.replace('NODE_URL = "http://localhost:8010"',
                        'NODE_URL = "http://127.0.0.1:8010"', 1)
    wsrc = wsrc.replace('value="http://localhost:8010"',
                        'value="http://127.0.0.1:8010"', 1)
    wh.write_text(wsrc, encoding="utf-8")
    print("[OK] web/index.html: NODE_URL -> 127.0.0.1")

print("[DONE] restart nodes: .\\scripts\\stop_all.ps1 ; .\\scripts\\run_all.ps1")