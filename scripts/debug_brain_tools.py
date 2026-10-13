"""
Диагностика Brain tools — прямые вызовы в обход LLM.

Запуск:
    .venv\\Scripts\\python.exe scripts\\debug_brain_tools.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.brain import BrainConfig, BrainTools, CLISigner


def show(title: str, result: dict) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def main() -> int:
    cfg = BrainConfig.from_env()
    signer = CLISigner("alice", cfg.node_url)
    tools = BrainTools(cfg, signer=signer)

    print(f"Node: {cfg.node_url}")
    print(f"Signer: {signer.name}, sender = {signer.sender_address}")

    # 1. Статус ноды
    show("1. chain_status", tools.chain_status())

    # 2. Список AIX-ID
    show("2. список AIX-ID", tools._get("/ids"))  # noqa: SLF001

    # 3. Пробуем зарегистрировать @naparnik — увидим точную ошибку сервера
    print("\n[!] Следующий шаг попробует создать AIX-ID @naparnik.")
    print("[!] Отвечай y/N на подтверждение. Ожидаем ошибку 'имя занято' или успех.")
    show("3. id_register @naparnik", tools.id_register("naparnik", avatar="🚀"))

    # 4. Медаль-каталог — какие медали уже выданы
    show("4. medal-каталог (первый 5)", {
        "ok": True,
        "data": {k: v for k, v in
                 (tools._get("/sbt/catalog").get("data") or {}).items()
                 if k == "medals"}
    })

    # 5. Медали bob — есть ли уже EARLY_BIRD
    show("5. медали bob", tools._get("/sbt/owner/AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC"))  # noqa: SLF001

    # 6. Пул ликвидности
    show("6. swap_pools", tools.swap_pools())

    # 7. Котировка с реальным pool_id
    pools = tools.swap_pools()
    if pools.get("ok"):
        pool_list = (pools["data"] or {}).get("pools", [])
        if pool_list:
            pid = pool_list[0]["id"]
            show(f"7. swap_quote pool={pid}",
                 tools.swap_quote(pid, "USDT-SIM", 50.0))
        else:
            print("\n  Пул не найден — swap_quote пропущен")

    return 0


if __name__ == "__main__":
    sys.exit(main())