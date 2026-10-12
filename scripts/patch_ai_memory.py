"""AIX OS — авто-патчер AI Memory.

Применяет все правки для интеграции AI Memory в:
  - network/server.py
  - cli/main.py
  - web/index.html

Идемпотентный: повторный запуск ничего не сломает.
Делает .bak-копии перед изменением.

Запуск:
    python scripts/patch_ai_memory.py
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


def log_ok(msg): print(f"{GREEN}✅ {msg}{RESET}")
def log_warn(msg): print(f"{YELLOW}⚠️  {msg}{RESET}")
def log_err(msg): print(f"{RED}❌ {msg}{RESET}")
def log_info(msg): print(f"{CYAN}ℹ️  {msg}{RESET}")


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak")
    if not bak.exists():
        shutil.copy2(path, bak)
        log_info(f"Создан бэкап: {bak.name}")


def insert_after(text: str, anchor: str, insert: str, marker: str) -> tuple[str, bool]:
    """Вставить insert после anchor, если marker ещё не встречается.

    Возвращает (новый текст, изменилось ли).
    """
    if marker in text:
        return text, False
    idx = text.find(anchor)
    if idx == -1:
        raise ValueError(f"Якорь не найден: {anchor[:60]!r}")
    end = idx + len(anchor)
    return text[:end] + insert + text[end:], True


def insert_before(text: str, anchor: str, insert: str, marker: str) -> tuple[str, bool]:
    if marker in text:
        return text, False
    idx = text.find(anchor)
    if idx == -1:
        raise ValueError(f"Якорь не найден: {anchor[:60]!r}")
    return text[:idx] + insert + text[idx:], True


def replace_once(text: str, old: str, new: str, marker: str) -> tuple[str, bool]:
    if marker in text:
        return text, False
    if old not in text:
        raise ValueError(f"Не найдено для замены: {old[:60]!r}")
    return text.replace(old, new, 1), True


# =============================================================================
# SERVER.PY
# =============================================================================

def patch_server() -> None:
    path = ROOT / "network" / "server.py"
    if not path.exists():
        log_err(f"Не найден: {path}")
        return
    backup(path)
    text = path.read_text(encoding="utf-8")

    # 1. Импорт
    anchor1 = (
        "from core.protocols.state_sync import (\n"
        "    export_state, import_state, apply_event,\n"
        "    make_gift_event, make_timelock_event, make_medal_event,\n"
        "    make_inheritance_event, make_id_event, make_burn_event, make_contact_event,\n"
        "    make_swap_event, make_poc_event, make_poc_pool_event,\n"
        ")"
    )
    insert1 = (
        "\nfrom core.protocols.ai_memory import (\n"
        "    AIMemoryManager, KINDS as AI_KINDS, PRIORITIES as AI_PRIORITIES,\n"
        "    KIND_EMOJI, PRIORITY_EMOJI,\n"
        ")"
    )
    text, _ = insert_after(text, anchor1, insert1,
                            marker="from core.protocols.ai_memory import")

    # 2. Pydantic-модель
    anchor2 = "class PoCPayRequest(BaseModel):\n    contribution_id: str"
    insert2 = (
        "\n\nclass AIRememberRequest(BaseModel):\n"
        "    text: str\n"
        '    kind: str = "THOUGHT"\n'
        '    priority: str = "NORMAL"\n'
        "    tags: list[str] = []\n"
        '    session: str = ""\n'
        '    chain_ref: str = ""'
    )
    text, _ = insert_after(text, anchor2, insert2,
                            marker="class AIRememberRequest")

    # 3. Инициализация
    anchor3 = "    poc_manager = PoCManager(poc_file, blockchain=blockchain)"
    insert3 = (
        "\n\n    ai_memory_path = Path(data_file).parent / \"ai_memory.json\"\n"
        "    ai_memory = AIMemoryManager(ai_memory_path)"
    )
    text, _ = insert_after(text, anchor3, insert3,
                            marker="ai_memory = AIMemoryManager")

    # 4. Строка в lifespan
    anchor4 = (
        '        print(f"[{port}] PoC: {len(poc_manager)} contributions, '
        'pool={poc_manager.pool.balance_aix():.2f} AIX")'
    )
    insert4 = '\n        print(f"[{port}] AI Memory: {ai_memory.count()} записей")'
    text, _ = insert_after(text, anchor4, insert4,
                            marker='AI Memory: {ai_memory.count()}')

    # 5. Поле в /status
    old5 = '            "poc_pool_aix": poc_manager.pool.balance_aix(),\n        }'
    new5 = (
        '            "poc_pool_aix": poc_manager.pool.balance_aix(),\n'
        '            "ai_memory_count": ai_memory.count(),\n'
        '        }'
    )
    text, _ = replace_once(text, old5, new5,
                            marker='"ai_memory_count": ai_memory.count()')

    # 6. Блок эндпоинтов перед P2P
    anchor6 = (
        "    # =========================================================================\n"
        "    # P2P\n"
        "    # =========================================================================\n"
    )
    insert6 = (
        "    # =========================================================================\n"
        "    # AI MEMORY (#AI-1)\n"
        "    # =========================================================================\n\n"
        "    @app.get(\"/ai/memory\")\n"
        "    def ai_memory_brief(max_critical: int = 10, max_latest: int = 20):\n"
        "        return {\n"
        "            \"count\": ai_memory.count(),\n"
        "            \"sessions\": ai_memory.sessions(),\n"
        "            \"brief\": ai_memory.brief(max_critical=max_critical, max_latest=max_latest),\n"
        "            \"stats\": ai_memory.stats(),\n"
        "        }\n\n"
        "    @app.get(\"/ai/memory/stats\")\n"
        "    def ai_memory_stats():\n"
        "        return ai_memory.stats()\n\n"
        "    @app.get(\"/ai/memory/latest\")\n"
        "    def ai_memory_latest(n: int = 20):\n"
        "        return {\"count\": n, \"memories\": [m.to_dict() for m in ai_memory.latest(n)]}\n\n"
        "    @app.get(\"/ai/memory/critical\")\n"
        "    def ai_memory_critical(n: int = 10):\n"
        "        return {\"count\": n, \"memories\": [m.to_dict() for m in ai_memory.critical(n)]}\n\n"
        "    @app.get(\"/ai/memory/session/{session}\")\n"
        "    def ai_memory_by_session(session: str):\n"
        "        memories = [m for m in ai_memory.all() if m.session == session]\n"
        "        return {\"session\": session, \"count\": len(memories),\n"
        "                \"memories\": [m.to_dict() for m in memories]}\n\n"
        "    @app.get(\"/ai/memory/tag/{tag}\")\n"
        "    def ai_memory_by_tag(tag: str):\n"
        "        memories = ai_memory.by_tag(tag)\n"
        "        return {\"tag\": tag, \"count\": len(memories),\n"
        "                \"memories\": [m.to_dict() for m in memories]}\n\n"
        "    @app.get(\"/ai/memory/kind/{kind}\")\n"
        "    def ai_memory_by_kind(kind: str):\n"
        "        memories = ai_memory.by_kind(kind)\n"
        "        return {\"kind\": kind.upper(), \"count\": len(memories),\n"
        "                \"memories\": [m.to_dict() for m in memories]}\n\n"
        "    @app.post(\"/ai/remember\")\n"
        "    def ai_remember(req: AIRememberRequest):\n"
        "        try:\n"
        "            mem = ai_memory.add(\n"
        "                text=req.text, kind=req.kind, priority=req.priority,\n"
        "                tags=req.tags, session=req.session or None,\n"
        "                chain_ref=req.chain_ref,\n"
        "            )\n"
        "        except ValueError as e:\n"
        "            raise HTTPException(400, str(e))\n"
        "        return {\n"
        "            \"status\": \"stored\",\n"
        "            \"id\": mem.hash[:12],\n"
        "            \"kind\": mem.kind,\n"
        "            \"priority\": mem.priority,\n"
        "            \"session\": mem.session,\n"
        "            \"ts\": mem.ts,\n"
        "            \"text\": mem.text,\n"
        "            \"total\": ai_memory.count(),\n"
        "        }\n\n"
    )
    text, _ = insert_before(text, anchor6, insert6,
                             marker="# AI MEMORY (#AI-1)")

    path.write_text(text, encoding="utf-8")
    log_ok(f"Пропатчен: {path.relative_to(ROOT)}")


# =============================================================================
# CLI/MAIN.PY
# =============================================================================

def patch_cli() -> None:
    path = ROOT / "cli" / "main.py"
    if not path.exists():
        log_err(f"Не найден: {path}")
        return
    backup(path)
    text = path.read_text(encoding="utf-8")

    # 1. Импорт
    anchor1 = "from crypto.address import is_valid_address"
    insert1 = (
        "\nfrom core.protocols.ai_memory import (\n"
        "    AIMemoryManager, KINDS as AI_KINDS, PRIORITIES as AI_PRIORITIES,\n"
        "    KIND_EMOJI, PRIORITY_EMOJI,\n"
        ")"
    )
    text, _ = insert_after(text, anchor1, insert1,
                            marker="from core.protocols.ai_memory import")

    # 2. Функции перед ГЛАВНАЯ
    anchor2 = (
        "# =============================================================================\n"
        "# ГЛАВНАЯ\n"
        "# ============================================================================="
    )
    insert2 = '''# =============================================================================
# AI MEMORY (#AI-1)
# =============================================================================

def _ai_memory_manager():
    return AIMemoryManager(config.DATA_DIR / "ai_memory.json")


def cmd_ai_remember(a):
    mgr = _ai_memory_manager()
    try:
        mem = mgr.add(text=a.text, kind=a.kind, priority=a.priority,
                      tags=a.tags, session=a.session, chain_ref=a.chain_ref or "")
    except ValueError as e:
        print(f"{Fore.RED}\\u274c {e}"); return 1
    ke = KIND_EMOJI.get(mem.kind, "\\u2022")
    pe = PRIORITY_EMOJI.get(mem.priority, "\\u2022")
    print(f"{Fore.GREEN}\\u2705 Записано: {ke} [{mem.kind}] {pe} {mem.priority}")
    print(f"   {mem.text}")
    print(f"   session={mem.session} ts={mem.ts} hash={mem.hash[:10]}")
    print(f"   всего в памяти: {mgr.count()}")
    return 0


def cmd_ai_brief(a):
    mgr = _ai_memory_manager()
    text = mgr.brief(max_critical=a.critical, max_latest=a.latest)
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8")
        print(f"{Fore.GREEN}\\u2705 Бриф записан: {a.output} ({len(text)} символов)")
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(text)
    return 0


def cmd_ai_stats(a):
    mgr = _ai_memory_manager()
    st = mgr.stats()
    print(f"{Fore.CYAN}\\U0001f9e0 AI Memory \\u2014 статистика")
    print(f"   Всего:      {Fore.YELLOW}{st['total']}")
    print(f"   Сессий:     {Fore.YELLOW}{st['sessions']}")
    print(f"   По типам:   {st['by_kind']}")
    print(f"   Приоритеты: {st['by_priority']}")
    return 0


def cmd_ai_list(a):
    mgr = _ai_memory_manager()
    if a.kind:
        memories = mgr.by_kind(a.kind)
    elif a.tag:
        memories = mgr.by_tag(a.tag)
    elif a.session:
        memories = [m for m in mgr.all() if m.session == a.session]
    else:
        memories = mgr.latest(a.limit)
    if not memories:
        print(f"{Fore.YELLOW}Пусто"); return 0
    rows = []
    for m in memories:
        ke = KIND_EMOJI.get(m.kind, "\\u2022")
        pe = PRIORITY_EMOJI.get(m.priority, "\\u2022")
        tags = ",".join(m.tags) if m.tags else ""
        rows.append([ke, m.kind, pe, m.priority, m.text[:40], m.session, tags])
    print(tabulate(rows, headers=["", "Kind", "", "Prio", "Text", "Session", "Tags"],
                   tablefmt="rounded_outline"))
    return 0


'''
    text, _ = insert_before(text, anchor2, insert2,
                             marker="# AI MEMORY (#AI-1)")

    # 3. Регистрация парсера перед args = p.parse_args()
    anchor3 = "    args = p.parse_args()\n    return args.func(args)"
    insert3 = '''    # \\U0001f9e0 ai \\u2014 AI Memory (#AI-1)
    pai = sub.add_parser("ai", help="\\U0001f9e0 AI Memory (#AI-1)")
    asub = pai.add_subparsers(dest="ai_cmd", required=True)

    ar = asub.add_parser("remember", help="Записать воспоминание")
    ar.add_argument("text")
    ar.add_argument("--kind", default="THOUGHT", choices=AI_KINDS)
    ar.add_argument("--priority", default="NORMAL", choices=AI_PRIORITIES)
    ar.add_argument("--tags", default="", help="через запятую: mempool,chain")
    ar.add_argument("--session", default=None)
    ar.add_argument("--chain-ref", dest="chain_ref", default="")
    ar.set_defaults(func=cmd_ai_remember)

    ab = asub.add_parser("brief", help="Собрать бриф")
    ab.add_argument("--output", "-o", default=None)
    ab.add_argument("--critical", type=int, default=10)
    ab.add_argument("--latest", type=int, default=20)
    ab.set_defaults(func=cmd_ai_brief)

    asub.add_parser("stats", help="Статистика").set_defaults(func=cmd_ai_stats)

    al = asub.add_parser("list", help="Список воспоминаний")
    al.add_argument("--kind", default=None, choices=AI_KINDS)
    al.add_argument("--tag", default=None)
    al.add_argument("--session", default=None)
    al.add_argument("--limit", "-n", type=int, default=20)
    al.set_defaults(func=cmd_ai_list)

'''
    text, _ = insert_before(text, anchor3, insert3,
                             marker='pai = sub.add_parser("ai"')

    path.write_text(text, encoding="utf-8")
    log_ok(f"Пропатчен: {path.relative_to(ROOT)}")


# =============================================================================
# WEB/INDEX.HTML
# =============================================================================

def patch_web() -> None:
    path = ROOT / "web" / "index.html"
    if not path.exists():
        log_err(f"Не найден: {path}")
        return
    backup(path)
    text = path.read_text(encoding="utf-8")

    # 1. Таб
    anchor1 = '<div class="tab" data-tab="artifacts">🔥 Артефакты</div>'
    insert1 = '\n        <div class="tab" data-tab="ai">🧠 AI Memory</div>'
    text, _ = insert_after(text, anchor1, insert1,
                            marker='data-tab="ai"')

    # 2. Панель
    anchor2 = (
        '    <div class="panel" id="panel-artifacts">\n'
        '        <h2>Burn-to-Mint коллекция</h2>\n'
        '        <div class="card" id="artifacts-list"><div class="empty">Загрузка...</div></div>\n'
        '    </div>'
    )
    insert2 = '''

    <div class="panel" id="panel-ai">
        <h2>🧠 AI Memory</h2>
        <div class="notice">Память AI-ассистента. Каждое важное событие — структурированное воспоминание.</div>

        <div class="grid">
            <div class="stat"><div class="label">Всего</div><div class="value" id="ai-stat-total">—</div></div>
            <div class="stat"><div class="label">Сессий</div><div class="value" id="ai-stat-sessions">—</div></div>
            <div class="stat"><div class="label">🔴 Critical</div><div class="value" id="ai-stat-critical">—</div></div>
            <div class="stat"><div class="label">🟠 Important</div><div class="value" id="ai-stat-important">—</div></div>
        </div>

        <h2>Записать воспоминание</h2>
        <div class="card">
            <label style="display:block; margin-bottom:6px; color:var(--muted); font-size:12px;">Текст</label>
            <input id="ai-text" type="text" placeholder="Пофиксил баг с mempool">
            <label style="display:block; margin-bottom:6px; color:var(--muted); font-size:12px;">Тип</label>
            <select id="ai-kind">
                <option value="THOUGHT">💭 THOUGHT</option>
                <option value="MILESTONE">🏆 MILESTONE</option>
                <option value="BUG_FIXED">🐛 BUG_FIXED</option>
                <option value="DECISION">⚖️ DECISION</option>
                <option value="LEARNING">📚 LEARNING</option>
                <option value="IDEA">💡 IDEA</option>
                <option value="SESSION_START">🚀 SESSION_START</option>
                <option value="SESSION_END">🏁 SESSION_END</option>
            </select>
            <label style="display:block; margin-bottom:6px; color:var(--muted); font-size:12px;">Приоритет</label>
            <select id="ai-priority">
                <option value="NORMAL">🟡 NORMAL</option>
                <option value="IMPORTANT">🟠 IMPORTANT</option>
                <option value="CRITICAL">🔴 CRITICAL</option>
                <option value="EPHEMERAL">⚪ EPHEMERAL</option>
            </select>
            <label style="display:block; margin-bottom:6px; color:var(--muted); font-size:12px;">Теги (через запятую)</label>
            <input id="ai-tags" type="text" placeholder="mempool,chain">
            <button onclick="aiRemember()" id="ai-btn">Записать</button>
            <div class="result" id="ai-result"></div>
        </div>

        <h2>Последние воспоминания</h2>
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
                <span style="color:var(--muted); font-size:13px;">Обновлено: <span id="ai-updated">—</span></span>
                <button class="secondary small" onclick="refreshAi()">🔄 Обновить</button>
            </div>
            <div id="ai-list"><div class="empty">Загрузка...</div></div>
        </div>
    </div>'''
    text, _ = insert_after(text, anchor2, insert2,
                            marker='id="panel-ai"')

    # 3. Таб-переключатель
    anchor3 = '        if (t.dataset.tab === "poc") refreshPocAll();'
    insert3 = '\n        if (t.dataset.tab === "ai") refreshAi();'
    text, _ = insert_after(text, anchor3, insert3,
                            marker='if (t.dataset.tab === "ai") refreshAi();')

    # 4. JS-функции перед // Listeners
    anchor4 = "// Listeners"
    insert4 = '''// AI MEMORY
async function refreshAi() {
    try {
        const d = await apiGet("/ai/memory");
        const st = d.stats;
        document.getElementById("ai-stat-total").textContent = st.total;
        document.getElementById("ai-stat-sessions").textContent = st.sessions;
        document.getElementById("ai-stat-critical").textContent = st.by_priority.CRITICAL || 0;
        document.getElementById("ai-stat-important").textContent = st.by_priority.IMPORTANT || 0;
        document.getElementById("ai-updated").textContent = new Date().toLocaleTimeString("ru-RU");

        const latest = await apiGet("/ai/memory/latest?n=15");
        const el = document.getElementById("ai-list");
        if (!latest.memories.length) {
            el.innerHTML = '<div class="empty">Память пуста. Запиши первое воспоминание 👆</div>';
            return;
        }
        const keMap = {SESSION_START:"🚀",SESSION_END:"🏁",MILESTONE:"🏆",BUG_FIXED:"🐛",DECISION:"⚖️",LEARNING:"📚",IDEA:"💡",THOUGHT:"💭"};
        const peMap = {CRITICAL:"🔴",IMPORTANT:"🟠",NORMAL:"🟡",EPHEMERAL:"⚪"};
        el.innerHTML = latest.memories.map(m => {
            const ke = keMap[m.kind] || "•";
            const pe = peMap[m.priority] || "•";
            const tags = m.tags.length ? m.tags.map(t => `<span class="badge rare">#${t}</span>`).join(" ") : "";
            return `<div style="padding:10px 0; border-bottom:1px solid rgba(0,240,255,0.1);">
                <div style="color:var(--gold); font-size:13px;">${ke} <strong>${m.kind}</strong> ${pe} ${m.priority}</div>
                <div style="color:var(--text); font-size:14px; margin:4px 0;">${m.text}</div>
                <div style="color:var(--muted); font-size:11px;">${m.ts} · session <code>${m.session}</code> ${tags}</div>
            </div>`;
        }).join("");
    } catch (e) {
        document.getElementById("ai-list").innerHTML = `<div class="empty">Ошибка: ${e.message}</div>`;
    }
}

async function aiRemember() {
    const text = document.getElementById("ai-text").value.trim();
    const kind = document.getElementById("ai-kind").value;
    const priority = document.getElementById("ai-priority").value;
    const tagsRaw = document.getElementById("ai-tags").value.trim();
    const res = document.getElementById("ai-result");
    if (!text) { res.className="result error show"; res.textContent="❌ Введи текст"; return; }
    res.className = "result show"; res.textContent = "⏳ Запись...";
    try {
        const d = await apiPost("/ai/remember", {
            text, kind, priority,
            tags: tagsRaw ? tagsRaw.split(",").map(t => t.trim()).filter(Boolean) : [],
        });
        res.textContent = `✅ Записано: ${d.id}\\nвсего: ${d.total}`;
        document.getElementById("ai-text").value = "";
        document.getElementById("ai-tags").value = "";
        await refreshAi();
    } catch (e) { res.classList.add("error"); res.textContent = "❌ " + e.message; }
}

'''
    text, _ = insert_before(text, anchor4, insert4,
                             marker="async function refreshAi()")

    # 5. refreshAll
    old5 = """async function refreshAll() {
    await refreshStatus();
    await refreshWallets();
    await refreshMedals();
    await refreshContacts();
    await refreshArtifacts();
}"""
    new5 = """async function refreshAll() {
    await refreshStatus();
    await refreshWallets();
    await refreshMedals();
    await refreshContacts();
    await refreshArtifacts();
    await refreshAi();
}"""
    text, _ = replace_once(text, old5, new5,
                            marker="    await refreshAi();\n}")

    path.write_text(text, encoding="utf-8")
    log_ok(f"Пропатчен: {path.relative_to(ROOT)}")


# =============================================================================
# MAIN
# =============================================================================

def main() -> int:
    print(f"{CYAN}═══════════════════════════════════════════════{RESET}")
    print(f"{YELLOW}  AIX OS — авто-патчер AI Memory{RESET}")
    print(f"{CYAN}═══════════════════════════════════════════════{RESET}\n")

    # Проверяем, что базовые файлы AI Memory на месте
    required = [
        ROOT / "core" / "protocols" / "ai_memory.py",
        ROOT / "scripts" / "ai_remember.py",
        ROOT / "scripts" / "ai_brief.py",
    ]
    for f in required:
        if not f.exists():
            log_err(f"Сначала создай: {f.relative_to(ROOT)}")
            return 1

    try:
        patch_server()
        patch_cli()
        patch_web()
    except Exception as e:
        log_err(f"Ошибка: {e}")
        return 1

    print()
    log_ok("Все патчи применены.")
    print()
    print(f"{CYAN}Проверка:{RESET}")
    print("  pytest tests/test_ai_memory.py -v")
    print("  python cli/main.py ai stats")
    print("  python -m network.server --port 8010 --data data/chain_A.json")
    print()
    print(f"{YELLOW}Откат: переименуй нужный .bak обратно в оригинал.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())