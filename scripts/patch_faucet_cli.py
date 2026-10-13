"""
Патч cli/main.py — добавляет команды aix faucet.

Что добавляет:
    aix faucet stats             — статистика крана
    aix faucet log [--limit N]   — журнал выдач
    aix faucet set-treasury <имя> — назначить кошелёк-казначей (локально)

Идемпотентен. Бэкап: main.py.faucet.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_faucet_cli.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "main.py"

MARKER = "def cmd_faucet_stats"


# ---------- 1. Импорт FaucetManager ----------

IMPORT_ANCHOR = "from core.governance.dao import DAOManager"
IMPORT_ADD = "\nfrom core.protocols.faucet import FaucetManager"


# ---------- 2. Функции команд ----------

MAIN_ANCHOR = (
    "# =============================================================================\n"
    "# ГЛАВНАЯ\n"
    "# ============================================================================="
)

FAUCET_BLOCK = '''# =============================================================================
# FAUCET
# =============================================================================

def _faucet_path(port: int = 8010) -> str:
    import config as _cfg
    return str(_cfg.DATA_DIR / f"faucet_{port}.json")


def cmd_faucet_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/faucet/stats")
    if not d:
        print(f"{Fore.RED}Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}AIX Faucet -- статистика")
    print(f"   Казначей:        {Fore.YELLOW}{d.get('treasury') or '(не назначен)'}")
    print(f"   Выдача:          {Fore.YELLOW}{d.get('amount_per_claim_aix')} AIX")
    print(f"   Cooldown IP:     {d.get('cooldown_ip_hours')} ч")
    print(f"   Лимит/час:       {d.get('hourly_limit')}")
    print(f"   Всего выдач:     {Fore.YELLOW}{d.get('total_claims', 0)}")
    print(f"   Всего отдано:    {Fore.YELLOW}{d.get('total_sent_aix', 0)} AIX")
    print(f"   За последний час: {d.get('claims_last_hour', 0)}")
    print(f"   За 24 часа:       {d.get('claims_last_24h', 0)}")
    return 0


def cmd_faucet_log(a):
    url = _node_url(a)
    limit = getattr(a, "limit", 50) or 50
    d = _node_get(url, f"/faucet/log?limit={limit}")
    if not d:
        print(f"{Fore.RED}Нода {url} не отвечает"); return 1
    entries = d.get("entries", [])
    print(f"{Fore.CYAN}AIX Faucet -- журнал (последние {len(entries)}):")
    if not entries:
        print(f"   {Fore.YELLOW}Пока пусто.")
        return 0
    rows = []
    for e in entries:
        rows.append([
            time.strftime("%Y-%m-%d %H:%M", time.localtime(e.get("ts", 0))),
            (e.get("address", "")[:24] + "...") if len(e.get("address", "")) > 24 else e.get("address", ""),
            e.get("amount_aix", 0),
            (e.get("tx_id", "")[:16] + "...") if e.get("tx_id") else "",
        ])
    print(tabulate(rows, headers=["Время", "Адрес", "AIX", "TX"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_faucet_set_treasury(a):
    import config as _cfg
    path = _cfg.DATA_DIR / "faucet_8010.json"
    mgr = FaucetManager(path)
    mgr.set_treasury(a.wallet)
    print(f"{Fore.GREEN}Казначей назначен: {a.wallet}")
    print(f"   Файл: {path}")
    print(f"   {Fore.YELLOW}Не забудь перезапустить ноды, чтобы казначей подхватился.")
    return 0


'''

# ---------- 3. Парсер ----------

ARGS_ANCHOR = "    args = p.parse_args()"

ARGS_BLOCK = '''    # FAUCET
    pf = sub.add_parser("faucet", help="AIX Faucet (кран)")
    pf.add_argument("--node", default=DEFAULT_NODE)
    fsub = pf.add_subparsers(dest="faucet_cmd", required=True)

    fsub.add_parser("stats", help="Статистика крана").set_defaults(
        func=cmd_faucet_stats)

    flog = fsub.add_parser("log", help="Журнал выдач")
    flog.add_argument("--limit", "-n", type=int, default=50)
    flog.set_defaults(func=cmd_faucet_log)

    fst = fsub.add_parser("set-treasury", help="Назначить кошелёк-казначей")
    fst.add_argument("wallet", help="Имя кошелька-казначея")
    fst.set_defaults(func=cmd_faucet_set_treasury)

'''


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(
            f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:120]!r}"
        )
    return src.replace(anchor, replacement, 1)


def main() -> int:
    if not CLI.exists():
        print(f"[FATAL] {CLI} не найден")
        return 1

    src = CLI.read_text(encoding="utf-8")

    if MARKER in src:
        print("[cli/main.py] уже пропатчен — пропуск")
        return 0

    bak = CLI.with_suffix(CLI.suffix + ".faucet.bak")
    bak.write_bytes(CLI.read_bytes())
    print(f"[cli/main.py] backup -> {bak.name}")

    src = _replace_once(src, IMPORT_ANCHOR,
                        IMPORT_ANCHOR + IMPORT_ADD,
                        "import")
    src = _replace_once(src, MAIN_ANCHOR,
                        FAUCET_BLOCK + MAIN_ANCHOR,
                        "faucet block")
    src = _replace_once(src, ARGS_ANCHOR,
                        ARGS_BLOCK + ARGS_ANCHOR,
                        "argparse")

    CLI.write_text(src, encoding="utf-8")
    print("[cli/main.py] OK: aix faucet stats|log|set-treasury добавлены")
    print()
    print("Готово. Дальше -- файл 4 (faucet_setup.py).")
    return 0


if __name__ == "__main__":
    sys.exit(main())