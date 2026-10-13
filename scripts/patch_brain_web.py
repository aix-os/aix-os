"""
Патч Web UI: добавляет вкладку 🧠 Brain.

Идемпотентен. Бэкап web/index.html -> index.html.brain.bak при первом патче.
Ищет якоря в разных вариантах — если не находит, НЕ трогает файл,
а печатает что искать.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_brain_web.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "index.html"
PANEL = ROOT / "scripts" / "_brain_panel.html"
JS = ROOT / "scripts" / "_brain_js.txt"

MARKER_PANEL = 'id="panel-brain"'
MARKER_JS = "function brainInit()"


def _find_tab_anchor(src: str) -> tuple[str, str] | None:
    """Найти якорь для вставки кнопки таба Brain.

    Возвращает (вариант, якорь) или None.
    Ищем любой из известных вариантов структуры табов.
    """
    candidates = [
        # data-tab="ai"
        ('data-tab="ai"', 'data-tab="ai"'),
        # id="tab-ai"
        ('id="tab-ai"', 'id="tab-ai"'),
        # text-based
        (">🧠 AI Memory<", '>🧠 AI Memory<'),
        (">AI Memory<", '>AI Memory<'),
    ]
    for label, needle in candidates:
        if needle in src:
            return label, needle
    return None


def _find_panel_anchor(src: str) -> tuple[str, str] | None:
    """Найти якорь для вставки панели Brain (рядом с panel-ai)."""
    candidates = [
        ('id="panel-ai"', 'id="panel-ai"'),
        ('data-panel="ai"', 'data-panel="ai"'),
        # рядом с DAO
        ('id="panel-dao"', 'id="panel-dao"'),
    ]
    for label, needle in candidates:
        if needle in src:
            return label, needle
    return None


def _find_script_anchor(src: str) -> tuple[str, str] | None:
    """Найти якорь для вставки JS — перед закрывающим </script>."""
    candidates = [
        ("\n</script>", "\n</script>"),
        ("</script>", "</script>"),
    ]
    for label, needle in candidates:
        if needle in src:
            return label, needle
    return None


def _find_tab_container_end(src: str, anchor_pos: int) -> int:
    """Найти конец блока, содержащего кнопку таба (обычно это </button>)."""
    # Простейший вариант — ищем '</button>' после якоря
    end = src.find("</button>", anchor_pos)
    if end == -1:
        # Может быть <a ...>
        end = src.find("</a>", anchor_pos)
    if end == -1:
        # Может быть div
        end = src.find("</div>", anchor_pos)
    return end


def _find_panel_end(src: str, panel_start: int) -> int:
    """Найти конец панели panel-ai — по балансировке div.

    Панели у нас плоские (без вложенных div в начале), но на всякий случай
    ищем следующий id="panel-" — это начало следующей панели.
    """
    # Ищем следующий id="panel-<что-то>"
    needle = 'id="panel-'
    next_pos = src.find(needle, panel_start + 20)  # +20 чтобы не найти себя
    if next_pos == -1:
        # Последняя панель — ищем до </body>
        return src.find("</body>", panel_start)
    # Вернуться к началу строки с этим id (это обычно '<div id="panel-...')
    line_start = src.rfind("\n", 0, next_pos)
    if line_start == -1:
        line_start = next_pos
    return line_start


def main() -> int:
    if not WEB.exists():
        print(f"[FATAL] {WEB} не найден")
        return 1
    if not PANEL.exists():
        print(f"[FATAL] {PANEL} не найден")
        return 1
    if not JS.exists():
        print(f"[FATAL] {JS} не найден")
        return 1

    src = WEB.read_text(encoding="utf-8")

    if MARKER_PANEL in src or MARKER_JS in src:
        print("[web/index.html] уже пропатчен — пропуск")
        return 0

    panel_html = PANEL.read_text(encoding="utf-8")
    brain_js = JS.read_text(encoding="utf-8")

    # --- 1. Кнопка таба ---
    tab_hit = _find_tab_anchor(src)
    if tab_hit is None:
        print("[FATAL] Не найден якорь кнопки таба.")
        print("  Искал: data-tab=\"ai\" / id=\"tab-ai\" / >🧠 AI Memory<")
        print("  Пришли мне web/index.html — я пересчитаю якорь.")
        return 1
    tab_label, tab_needle = tab_hit
    tab_pos = src.find(tab_needle)
    tab_end = _find_tab_container_end(src, tab_pos)
    if tab_end == -1:
        print(f"[FATAL] Нашёл якорь таба ({tab_label}), но не могу определить "
              f"конец блока кнопки.")
        return 1

    # Определяем таг кнопки таба
    tab_open = src.rfind("<", 0, tab_pos)
    tag_close = src.find(">", tab_end) + 1
    tab_block = src[tab_open:tag_close]

    # Собираем кнопку Brain по образцу
    tab_brain = tab_block.replace("ai", "brain", 1)  # data-tab="ai" -> brain
    # Если это текст "🧠 AI Memory" — меняем на Brain
    if "🧠 AI Memory" in tab_brain:
        tab_brain = tab_brain.replace("🧠 AI Memory", "🧠 Brain")
    elif "AI Memory" in tab_brain:
        tab_brain = tab_brain.replace("AI Memory", "🧠 Brain")
    else:
        # На всякий случай: если не нашли текст, вставляем кнопку явно
        tab_brain = tab_block.replace('data-tab="ai"', 'data-tab="brain"')
        tab_brain = tab_brain.replace('id="tab-ai"', 'id="tab-brain"')

    # Вставляем кнопку Brain сразу после кнопки AI Memory
    src = src[:tag_close] + "\n" + tab_brain + src[tag_close:]

    # --- 2. Панель Brain ---
    panel_hit = _find_panel_anchor(src)
    if panel_hit is None:
        print("[FATAL] Не найден якорь панели (panel-ai / panel-dao).")
        print("  Пришли мне web/index.html — пересчитаю.")
        return 1
    panel_label, panel_needle = panel_hit
    panel_pos = src.find(panel_needle)
    panel_open = src.rfind("<", 0, panel_pos)
    panel_end = _find_panel_end(src, panel_open)
    if panel_end == -1:
        print(f"[FATAL] Нашёл якорь панели ({panel_label}), но не могу найти "
              f"конец panel-ai.")
        return 1

    # Вставляем panel-brain ПЕРЕД panel-ai (или panel-dao)
    insertion = "\n" + panel_html.strip() + "\n\n"
    src = src[:panel_open] + insertion + src[panel_open:]

    # --- 3. JS ---
    script_hit = _find_script_anchor(src)
    if script_hit is None:
        print("[FATAL] Не найден </script> для вставки JS.")
        return 1
    script_label, script_needle = script_hit
    script_pos = src.rfind(script_needle)
    src = src[:script_pos] + "\n\n" + brain_js + "\n" + src[script_pos:]

    # --- 4. Хук init: вызывать brainInit при переключении на вкладку ---
    # Ищем showPanel / switchTab / activateTab
    hook_installed = False
    for name in ("function showPanel", "function switchTab", "function activateTab"):
        pos = src.find(name)
        if pos != -1:
            # Найти открывающую фигурную скобку после имени
            brace = src.find("{", pos)
            if brace != -1:
                # Вставить в начало тела функции
                insert = (
                    '\n  if (typeof brainInit === "function") '
                    'try { brainInit(); } catch(e) {}'
                )
                src = src[:brace + 1] + insert + src[brace + 1:]
                hook_installed = True
            break

    # Фоллбек: если хука нет, дернём brainInit по DOMContentLoaded
    if not hook_installed:
        # Ищем </body> и вставляем мини-скрипт
        body_pos = src.rfind("</body>")
        if body_pos != -1:
            boot = (
                "\n<script>\n"
                "document.addEventListener('DOMContentLoaded', function(){\n"
                "  if (typeof brainInit === 'function') brainInit();\n"
                "});\n"
                "</script>\n"
            )
            src = src[:body_pos] + boot + src[body_pos:]

    # --- 5. Бэкап и запись ---
    bak = WEB.with_suffix(WEB.suffix + ".brain.bak")
    bak.write_bytes(WEB.read_bytes())
    print(f"[web/index.html] backup -> {bak.name}")

    WEB.write_text(src, encoding="utf-8")
    print("[web/index.html] OK: таб 🧠 Brain + panel-brain + JS добавлены")
    print()
    print("✅ Патч Brain Web завершён.")
    print("   Перезапускать ноды НЕ нужно (web/index.html отдаётся статикой).")
    print("   Открой:  http://localhost:9000")
    print("   Нажми вкладку «🧠 Brain».")
    return 0


if __name__ == "__main__":
    sys.exit(main())