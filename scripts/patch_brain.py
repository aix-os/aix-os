"""
Патч Brain в network/server.py и cli/main.py.

Идемпотентен: если маркер 'ai.brain' или '/brain/ask' уже есть — пропускает.
Бэкапы: *.bak рядом с оригиналами.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_brain.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "network" / "server.py"
CLI = ROOT / "cli" / "main.py"


def backup(p: Path) -> None:
    b = p.with_suffix(p.suffix + ".bak")
    b.write_bytes(p.read_bytes())
    print(f"  backup -> {b.name}")


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:80]!r}")
    return src.replace(anchor, replacement, 1)


# ============================================================================
# SERVER
# ============================================================================

SERVER_IMPORT_ANCHOR = "from core.governance.dao import DAOManager"
SERVER_IMPORT_ADD = "\nfrom ai.brain import BrainAgent, BrainConfig"

SERVER_MODEL_ANCHOR = "class DAOCancelRequest(BaseModel):\n    by: str"
SERVER_MODEL_ADD = (
    "\n\n\nclass BrainAskRequest(BaseModel):\n"
    "    message: str\n"
    "    model: str | None = None"
)

SERVER_INIT_ANCHOR = (
    "    dao_manager = DAOManager(dao_path, blockchain=blockchain, "
    "sbt_manager=sbt_manager, poc_manager=poc_manager)"
)
SERVER_INIT_ADD = "\n\n    brain_config = BrainConfig.from_env()"

SERVER_P2P_ANCHOR = (
    '    # =========================================================================\n'
    '    # P2P\n'
    '    # =========================================================================\n'
    '\n'
    '    @app.get("/peers")'
)

SERVER_BRAIN_BLOCK = '''    # =========================================================================
    # BRAIN (AI-напарник)
    # =========================================================================

    @app.get("/brain/health")
    def brain_health():
        try:
            agent = BrainAgent(brain_config)
        except Exception as e:
            raise HTTPException(500, f"Brain недоступен: {e}")
        return agent.health()

    @app.post("/brain/ask")
    def brain_ask(req: BrainAskRequest):
        cfg = brain_config
        if req.model:
            cfg = cfg.with_model(req.model)
        try:
            agent = BrainAgent(cfg)
            answer = agent.ask(req.message)
        except Exception as e:
            raise HTTPException(500, f"Brain error: {e}")
        return {"status": "ok", "answer": answer, "model": cfg.model}

'''


def patch_server() -> None:
    print(f"\n[server.py] {SERVER}")
    src = SERVER.read_text(encoding="utf-8")

    if "/brain/ask" in src or "from ai.brain import" in src:
        print("  уже пропатчен — пропуск")
        return

    backup(SERVER)

    src = _replace_once(src, SERVER_IMPORT_ANCHOR,
                        SERVER_IMPORT_ANCHOR + SERVER_IMPORT_ADD,
                        "server: import")
    src = _replace_once(src, SERVER_MODEL_ANCHOR,
                        SERVER_MODEL_ANCHOR + SERVER_MODEL_ADD,
                        "server: pydantic model")
    src = _replace_once(src, SERVER_INIT_ANCHOR,
                        SERVER_INIT_ANCHOR + SERVER_INIT_ADD,
                        "server: create_app init")
    src = _replace_once(src, SERVER_P2P_ANCHOR,
                        SERVER_BRAIN_BLOCK + SERVER_P2P_ANCHOR,
                        "server: P2P anchor")

    SERVER.write_text(src, encoding="utf-8")
    print("  OK: /brain/health, /brain/ask добавлены")


# ============================================================================
# CLI
# ============================================================================

CLI_MAIN_ANCHOR = (
    "# =============================================================================\n"
    "# ГЛАВНАЯ\n"
    "# ============================================================================="
)

CLI_BRAIN_BLOCK = '''# =============================================================================
# BRAIN (AI-напарник)
# =============================================================================

def cmd_brain_health(a):
    from ai.brain import BrainAgent
    agent = BrainAgent()
    h = agent.health()
    print(f"{Fore.CYAN}\\U0001f9e0 AIX Brain -- health")
    ok = h["backend_available"]
    c = Fore.GREEN if ok else Fore.RED
    print(f"   Backend:   {c}{'OK' if ok else 'DOWN'}{Fore.RESET} {h['backend_url']}")
    print(f"   Model:     {Fore.YELLOW}{h['model']}")
    mk = h["model_installed"]
    cm = Fore.GREEN if mk else Fore.YELLOW
    print(f"   Installed: {cm}{mk}{Fore.RESET}")
    if h.get("models_available"):
        shown = ", ".join(h["models_available"][:5])
        print(f"   Models:    {shown}")
    mem = h["memory_available"]
    print(f"   Memory:    {Fore.GREEN + 'OK' if mem else Fore.RED + 'NO'}{Fore.RESET}")
    print(f"   Node URL:  {h['node_url']}")
    print(f"   Tools:     {', '.join(h['tools'])}")
    return 0 if ok else 1


def cmd_brain_ask(a):
    from ai.brain import BrainAgent, BrainConfig
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    agent = BrainAgent(cfg)
    if not agent.client.is_available():
        print(f"{Fore.RED}\\u274c Ollama недоступен на {cfg.base_url}")
        print(f"   Установи: https://ollama.com")
        print(f"   Затем:    ollama pull {cfg.model}")
        return 1
    print(f"{Fore.CYAN}\\U0001f9e0 Brain думает ({cfg.model})...")
    try:
        answer = agent.ask(a.message)
    except Exception as e:
        print(f"{Fore.RED}\\u274c {e}")
        return 1
    print(f"{Fore.GREEN}\\U0001f4ac {answer}")
    return 0


def cmd_brain_remember(a):
    from ai.brain import BrainAgent
    agent = BrainAgent()
    tags = [t.strip() for t in (a.tags or "").split(",") if t.strip()]
    res = agent.remember(
        title=a.title, kind=a.kind, priority=a.priority,
        body=a.body or "", tags=tags or None,
    )
    if not res.get("ok"):
        print(f"{Fore.RED}\\u274c {res.get('error', 'unknown')}")
        return 1
    print(f"{Fore.GREEN}\\u2705 Записано в AI Memory")
    print(f"   {a.title}")
    return 0


def cmd_brain_chat(a):
    from ai.brain import BrainAgent, BrainConfig
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    agent = BrainAgent(cfg)
    if not agent.client.is_available():
        print(f"{Fore.RED}\\u274c Ollama недоступен на {cfg.base_url}")
        return 1
    print(f"{Fore.MAGENTA}\\U0001f9e0 AIX Brain -- интерактивный режим ({cfg.model})")
    print(f"   {Fore.YELLOW}exit/quit -- выход, reset -- очистить историю{Fore.RESET}")
    while True:
        try:
            line = input(f"{Fore.CYAN}вы> {Fore.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            break
        if line.lower() == "reset":
            agent.reset()
            print(f"{Fore.YELLOW}История очищена.{Fore.RESET}")
            continue
        try:
            answer = agent.ask(line)
        except Exception as e:
            print(f"{Fore.RED}\\u274c {e}")
            continue
        print(f"{Fore.GREEN}\\U0001f9e0 {answer}\\n")
    return 0


'''

CLI_ARGS_ANCHOR = "    args = p.parse_args()"

CLI_ARGS_BLOCK = '''    # BRAIN -- AI-напарник
    pbrain = sub.add_parser("brain", help="AIX Brain (локальная LLM)")
    pbrain.add_argument("--node", default=DEFAULT_NODE)
    pb_sub = pbrain.add_subparsers(dest="brain_cmd", required=True)

    pb_sub.add_parser("health", help="Проверить бэкенд и модель").set_defaults(
        func=cmd_brain_health)

    pba = pb_sub.add_parser("ask", help="Спросить AIX Brain")
    pba.add_argument("message")
    pba.add_argument("--model", default=None)
    pba.set_defaults(func=cmd_brain_ask)

    pbr = pb_sub.add_parser("remember", help="Записать в AI Memory")
    pbr.add_argument("title")
    pbr.add_argument("--kind", default="THOUGHT", choices=AI_KINDS)
    pbr.add_argument("--priority", default="NORMAL", choices=AI_PRIORITIES)
    pbr.add_argument("--body", default="")
    pbr.add_argument("--tags", default="")
    pbr.set_defaults(func=cmd_brain_remember)

    pbc = pb_sub.add_parser("chat", help="Интерактивный диалог")
    pbc.add_argument("--model", default=None)
    pbc.set_defaults(func=cmd_brain_chat)

'''


def patch_cli() -> None:
    print(f"\n[main.py] {CLI}")
    src = CLI.read_text(encoding="utf-8")

    if "cmd_brain_ask" in src:
        print("  уже пропатчен — пропуск")
        return

    backup(CLI)

    src = _replace_once(src, CLI_MAIN_ANCHOR,
                        CLI_BRAIN_BLOCK + CLI_MAIN_ANCHOR,
                        "cli: main section anchor")
    src = _replace_once(src, CLI_ARGS_ANCHOR,
                        CLI_ARGS_BLOCK + CLI_ARGS_ANCHOR,
                        "cli: parse_args anchor")

    CLI.write_text(src, encoding="utf-8")
    print("  OK: aix brain health|ask|remember|chat добавлены")


# ============================================================================

def main() -> int:
    if not SERVER.exists():
        print(f"[FATAL] {SERVER} не найден")
        return 1
    if not CLI.exists():
        print(f"[FATAL] {CLI} не найден")
        return 1

    patch_server()
    patch_cli()

    print("\n\u2705 Патч Brain завершён.")
    print("   Дальше:")
    print("     1) Перезапусти ноды:  .\\scripts\\stop_all.ps1 ; .\\scripts\\run_all.ps1")
    print("     2) Проверь:           .venv\\Scripts\\python.exe cli\\main.py brain health")
    print("     3) Тесты:             .venv\\Scripts\\python.exe -m pytest tests\\test_brain.py -v")
    return 0


if __name__ == "__main__":
    sys.exit(main())