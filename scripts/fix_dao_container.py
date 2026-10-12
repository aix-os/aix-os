from pathlib import Path
import shutil, sys

HTML = Path("web/index.html")
src = HTML.read_text(encoding="utf-8")

dao_marker = '    <div class="panel" id="panel-dao">'
dao_idx = src.find(dao_marker)
if dao_idx == -1:
    print("[FAIL] panel-dao not found"); sys.exit(1)

# Step 1: remove premature </div> (container close) right before panel-dao
if not src[:dao_idx].endswith('</div>\n'):
    print("[SKIP] already fixed or structure differs")
    sys.exit(0)

src = src[:dao_idx - len('</div>\n')] + src[dao_idx:]
print("[OK] removed premature container close")

# Step 2: add container close before <footer>
needle = '</div>\n\n<footer>'
if needle not in src:
    print("[FAIL] cannot find insertion point before <footer>")
    print("tail:", repr(src[-300:]))
    sys.exit(1)

src = src.replace(needle, '</div>\n</div>\n\n<footer>', 1)
print("[OK] added container close before footer")

bak = HTML.with_suffix(".html.bak3")
shutil.copy2(HTML, bak)
print("[ OK ] backup -> " + bak.name)
HTML.write_text(src, encoding="utf-8")
print("[DONE] hard-reload browser: Ctrl+F5")