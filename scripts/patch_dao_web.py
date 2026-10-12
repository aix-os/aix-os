"""AIX OS -- patch Web UI: DAO tab (v3, fixed insertion point)."""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "web" / "index.html"

def main():
    if not HTML.exists():
        print("[FAIL] not found: " + str(HTML)); sys.exit(1)

    src = HTML.read_text(encoding="utf-8")
    if 'id="panel-dao"' in src:
        print("[SKIP] already patched"); sys.exit(0)

    bak = HTML.with_suffix(".html.bak2")
    shutil.copy2(HTML, bak); print("[ OK ] backup -> " + bak.name)

    # -------- 1. tab: insert AFTER closing </div> of AI Memory tab --------
    anchor = 'data-tab="ai">'
    idx = src.find(anchor)
    if idx == -1:
        print("[FAIL] tab anchor not found"); sys.exit(1)
    end = src.find("</div>", idx)
    if end == -1:
        print("[FAIL] tab close not found"); sys.exit(1)
    end += len("</div>")  # <-- FIX: shift past closing tag
    tab_line = '\n        <div class="tab" data-tab="dao">\U0001f5f3 DAO</div>'
    src = src[:end] + tab_line + src[end:]
    print("[ OK ] tab added (after AI Memory)")

    # -------- 2. panel: insert right before <footer> --------
    ai_idx = src.find('id="panel-ai"')
    if ai_idx == -1:
        print("[FAIL] panel-ai not found"); sys.exit(1)
    footer_idx = src.find("<footer>", ai_idx)
    if footer_idx == -1:
        print("[FAIL] footer not found after panel-ai"); sys.exit(1)
    insert_at = src.rfind("</div>", ai_idx, footer_idx)
    if insert_at == -1:
        print("[FAIL] panel close not found"); sys.exit(1)
    insert_at += len("</div>")

    PANEL = open(ROOT / "scripts" / "_dao_panel.html", encoding="utf-8").read()
    src = src[:insert_at] + PANEL + src[insert_at:]
    print("[ OK ] panel added")

    # -------- 3. switch-tab --------
    sw_anchor = 'if (t.dataset.tab === "ai") refreshAi();'
    if sw_anchor not in src:
        print("[FAIL] switch anchor not found"); sys.exit(1)
    src = src.replace(
        sw_anchor,
        sw_anchor + '\n        if (t.dataset.tab === "dao") refreshDao();',
        1,
    )
    print("[ OK ] switch-tab added")

    # -------- 4. JS block --------
    js_anchor = "async function refreshAi() {"
    if js_anchor not in src:
        print("[FAIL] JS anchor not found"); sys.exit(1)
    js_block = open(ROOT / "scripts" / "_dao_js.txt", encoding="utf-8").read()
    src = src.replace(js_anchor, js_block + "\n" + js_anchor, 1)
    print("[ OK ] JS funcs added")

    HTML.write_text(src, encoding="utf-8")
    print("[DONE] open http://localhost:9000, Ctrl+F5")


if __name__ == "__main__":
    main()