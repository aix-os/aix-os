"""
Патч CLI: добавляет --wallet в brain ask/chat и команду aix brain send.

Идемпотентен. Бэкап cli/main.py -> main.py.bak (один раз, при первом патче).

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_brain_send.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "main.py"

MARKER = "def cmd_brain_send(a):"


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:120]!r}")
    return src.replace(anchor, replacement, 1)


# --- 1. cmd_brain_ask: подключить signer ---

ASK_OLD = '''def cmd_brain_ask(a):
    from ai.brain import BrainAgent, BrainConfig
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    agent = BrainAgent(cfg)
'''

ASK_NEW = '''def cmd_brain_ask(a):
    from ai.brain import BrainAgent, BrainConfig, CLISigner, NullSigner
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    signer = CLISigner(a.wallet, cfg.node_url) if getattr(a, "wallet", None) else NullSigner()
    agent = BrainAgent(cfg, signer=signer)
'''


# --- 2. cmd_brain_chat: подключить signer ---

CHAT_OLD = '''def cmd_brain_chat(a):
    from ai.brain import BrainAgent, BrainConfig
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    agent = BrainAgent(cfg)
'''

CHAT_NEW = '''def cmd_brain_chat(a):
    from ai.brain import BrainAgent, BrainConfig, CLISigner, NullSigner
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    signer = CLISigner(a.wallet, cfg.node_url) if getattr(a, "wallet", None) else NullSigner()
    agent = BrainAgent(cfg, signer=signer)
'''


# --- 3. Новая функция cmd_brain_send + вставка перед "# ГЛАВНАЯ" ---

MAIN_ANCHOR = (
    "# =============================================================================\n"
    "# ГЛАВНАЯ\n"
    "# ============================================================================="
)

SEND_FUNC = '''# =============================================================================
# BRAIN SEND -- отправка AIX через CLI
# =============================================================================

def cmd_brain_send(a):
    from ai.brain import BrainTools, BrainConfig, CLISigner
    cfg = BrainConfig.from_env()
    signer = CLISigner(a.wallet, cfg.node_url)
    tools = BrainTools(cfg, signer=signer)
    res = tools.safe_send(a.recipient, a.amount, a.message or "")
    if res.get("ok"):
        print(f"{Fore.GREEN}\\u2705 Отправлено")
        print(f"   TX ID: {res.get('tx_id', '')[:32]}...")
        print(f"   Разослано пирам: {res.get('broadcast_to_peers', 0)}")
        return 0
    if res.get("cancelled"):
        print(f"{Fore.YELLOW}\\u26a0\\ufe0f  Отменено пользователем")
        return 0
    print(f"{Fore.RED}\\u274c {res.get('error', 'не отправлено')}")
    return 1


'''


# --- 4. argparse: --wallet для ask/chat + подкоманда send ---

ASK_ARGS_OLD = '''    pba = pb_sub.add_parser("ask", help="Спросить AIX Brain")
    pba.add_argument("message")
    pba.add_argument("--model", default=None)
    pba.set_defaults(func=cmd_brain_ask)
'''

ASK_ARGS_NEW = '''    pba = pb_sub.add_parser("ask", help="Спросить AIX Brain")
    pba.add_argument("message")
    pba.add_argument("--model", default=None)
    pba.add_argument("--wallet", default=None,
                     help="Кошелёк для безопасной отправки (y/N)")
    pba.set_defaults(func=cmd_brain_ask)
'''

CHAT_ARGS_OLD = '''    pbc = pb_sub.add_parser("chat", help="Интерактивный диалог")
    pbc.add_argument("--model", default=None)
    pbc.set_defaults(func=cmd_brain_chat)
'''

CHAT_ARGS_NEW = '''    pbc = pb_sub.add_parser("chat", help="Интерактивный диалог")
    pbc.add_argument("--model", default=None)
    pbc.add_argument("--wallet", default=None,
                     help="Кошелёк для безопасной отправки (y/N)")
    pbc.set_defaults(func=cmd_brain_chat)

    pbs = pb_sub.add_parser("send", help="Отправить AIX (y/N + подпись)")
    pbs.add_argument("wallet", help="Имя кошелька-отправителя")
    pbs.add_argument("recipient", help="AIX-адрес, @id, имя или phone:+7...")
    pbs.add_argument("amount", type=float, help="Сумма в AIX")
    pbs.add_argument("--message", "-m", default="")
    pbs.set_defaults(func=cmd_brain_send)
'''


def main() -> int:
    if not CLI.exists():
        print(f"[FATAL] {CLI} не найден")
        return 1

    src = CLI.read_text(encoding="utf-8")

    if MARKER in src:
        print("[cli/main.py] уже пропатчен — пропуск")
        return 0

    # Бэкап
    bak = CLI.with_suffix(CLI.suffix + ".send.bak")
    bak.write_bytes(CLI.read_bytes())
    print(f"[cli/main.py] backup -> {bak.name}")

    src = _replace_once(src, ASK_OLD, ASK_NEW, "cmd_brain_ask body")
    src = _replace_once(src, CHAT_OLD, CHAT_NEW, "cmd_brain_chat body")
    src = _replace_once(src, MAIN_ANCHOR, SEND_FUNC + MAIN_ANCHOR, "main section")
    src = _replace_once(src, ASK_ARGS_OLD, ASK_ARGS_NEW, "ask argparse")
    src = _replace_once(src, CHAT_ARGS_OLD, CHAT_ARGS_NEW, "chat argparse + send")

    CLI.write_text(src, encoding="utf-8")
    print("[cli/main.py] OK: --wallet + brain send добавлены")
    print()
    print("\u2705 Патч Brain Send завершён.")
    print("   Перезапуск не нужен (CLI читается каждый раз заново).")
    print("   Проверь:")
    print("     .venv\\Scripts\\python.exe cli\\main.py brain send alice bob 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())