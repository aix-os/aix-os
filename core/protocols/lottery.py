"""
AIX OS — AIX Lottery (#12).

Лотерея честности: каждый блок имеет шанс 1/N выиграть для случайного адреса.

Правила:
1. Детерминированный seed от previous_hash + timestamp
2. Если seed % LOTTERY_CHANCE == 0 — блок счастливый
3. Победитель выбирается из всех активных адресов по хешу
4. Победитель получает LOTTERY_PRIZE AIX (создаётся как LOTTERY-транзакция)

Никто не знает исход заранее.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


# Параметры лотереи
LOTTERY_CHANCE = 3       # 1 шанс на 1000 блоков (поставь 20 для теста)
LOTTERY_PRIZE = 100         # 100 AIX победителю


def block_seed(block) -> int:
    """
    Детерминированный seed для блока.
    Использует previous_hash + timestamp — не зависит от nonce и не меняется.
    """
    prev = block.previous_hash or "0" * 64
    prev_int = int(prev[:16], 16)
    ts_int = int(block.timestamp)
    return prev_int ^ (ts_int * 2654435761)


def is_lottery_block(block) -> bool:
    """Является ли блок счастливым."""
    return block_seed(block) % LOTTERY_CHANCE == 0


def pick_lottery_winner(blockchain, block) -> str | None:
    """
    Детерминированно выбирает победителя из активных адресов.
    Исключает майнера текущего блока.
    Возвращает адрес или None, если кандидатов нет.
    """
    candidates: set[str] = set()
    for b in blockchain.chain:
        for tx in b.transactions:
            if tx.sender and tx.sender not in ("COINBASE", "LOTTERY"):
                candidates.add(tx.sender)
            if tx.recipient:
                candidates.add(tx.recipient)

    # Исключаем майнера текущего блока
    for tx in block.transactions:
        if tx.sender == "COINBASE":
            candidates.discard(tx.recipient)
            break

    if not candidates:
        return None

    seed = block_seed(block)
    candidates_sorted = sorted(candidates)
    idx = seed % len(candidates_sorted)
    return candidates_sorted[idx]


def compute_lottery_stats(blockchain) -> dict:
    """Собирает статистику по лотерее из всей цепочки."""
    wins: list[dict] = []
    total_prize = 0
    for b in blockchain.chain:
        for tx in b.transactions:
            if tx.sender == "LOTTERY":
                wins.append({
                    "block": b.index,
                    "block_hash": b.hash,
                    "winner": tx.recipient,
                    "amount_aix": tx.amount / config.SATOSHI,
                    "timestamp": b.timestamp,
                })
                total_prize += tx.amount

    return {
        "total_wins": len(wins),
        "total_prize_aix": total_prize / config.SATOSHI,
        "prize_per_win_aix": LOTTERY_PRIZE,
        "chance": f"1/{LOTTERY_CHANCE}",
        "total_blocks": blockchain.height() + 1,
        "wins": wins,
    }