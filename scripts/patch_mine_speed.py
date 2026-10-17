"""
AIX OS — патч ускорения майнинга.

Проблема: /mine сохраняет chain_A.json после КАЖДОГО блока.
При майнинге 20 000 блоков это 20 000 fsync × ~3 МБ = 60 ГБ диска.
Каждый блок ждёт ~0.5-1 сек. Итого 5+ часов на 1 000 000 AIX.

Решение: сохранять chain раз в N блоков (по умолчанию 1 = как было).
При MINE_SAVE_EVERY_N_BLOCKS=100 — блоки идут за ~0.05-0.1 сек.

Также: MINE_BROADCAST=False отключает рассылку каждого блока пирам.
Без этого нода B будет делать такой же fsync и тормозить всю сеть.

Добавляем в lifespan-финал: финальный save при shutdown,
чтобы не потерять последние блоки в буфере.

Идемпотентен. Бэкап: *.mine.bak.

Запуск:
    .venv\\Scripts\\python.exe scripts\\patch_mine_speed.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config.py"
SERVER = ROOT / "network" / "server.py"

MARKER_SERVER = "# MINE-SPEED-OPTIMIZED"
MARKER_CONFIG = "MINE_SAVE_EVERY_N_BLOCKS"


def _backup(p: Path, suffix: str = ".mine.bak") -> None:
    b = p.with_suffix(p.suffix + suffix)
    if not b.exists():
        b.write_bytes(p.read_bytes())


def _replace_once(src: str, anchor: str, replacement: str, label: str) -> str:
    if anchor not in src:
        raise SystemExit(
            f"[FATAL] Якорь не найден: {label}\n  -> {anchor[:120]!r}"
        )
    return src.replace(anchor, replacement, 1)


# ---------- 1. config.py — добавляем новые константы ----------

CONFIG_ANCHOR = "SATOSHI = 10 ** DECIMALS"
CONFIG_ADD = '''

# =============================================================================
# МАЙНИНГ — производительность
# =============================================================================

# Как часто сохранять chain в файл при майнинге.
# 1 = после каждого блока (безопасно, но медленно)
# 100 = раз в 100 блоков (быстро, но при крахе потеряются последние блоки)
MINE_SAVE_EVERY_N_BLOCKS = 1

# Рассылать каждый новый блок пирам.
# True = безопасно, но медленно (пир делает свой fsync)
# False = быстро, но пиры отстают, синхронизировать потом
MINE_BROADCAST = True
'''


# ---------- 2. server.py — условное сохранение в /mine ----------

MINE_SAVE_OLD = '''        ok, msg = blockchain.add_block(new_block)
        if not ok:
            raise HTTPException(500, f"Не удалось добавить блок: {msg}")

        storage.save(blockchain)
        broadcast_count = 0
        if req.broadcast:
            broadcast_count = peer_manager.broadcast_block(new_block.to_dict())'''

MINE_SAVE_NEW = '''        ok, msg = blockchain.add_block(new_block)
        if not ok:
            raise HTTPException(500, f"Не удалось добавить блок: {msg}")

        # MINE-SPEED-OPTIMIZED: сохраняем не каждый блок, а раз в N
        save_every = getattr(config, "MINE_SAVE_EVERY_N_BLOCKS", 1)
        if save_every <= 1 or new_block.index % save_every == 0:
            storage.save(blockchain)

        # MINE-SPEED-OPTIMIZED: рассылка блока пирам — опционально
        broadcast_count = 0
        if req.broadcast and getattr(config, "MINE_BROADCAST", True):
            broadcast_count = peer_manager.broadcast_block(new_block.to_dict())'''


# ---------- 3. lifespan — финальный save при shutdown ----------

LIFESPAN_ANCHOR = '''        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass'''

LIFESPAN_NEW = '''        yield

        # MINE-SPEED-OPTIMIZED: финальный save при shutdown —
        # чтобы не потерять блоки, что были в буфере.
        try:
            storage.save(blockchain)
            print(f"[{port}] Финальный save: высота {blockchain.height()}")
        except Exception as e:
            print(f"[{port}] WARN: финальный save упал: {e}")

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass'''


def patch_config_file() -> bool:
    print(f"[config.py]")
    if not CONFIG.exists():
        print(f"  [FATAL] {CONFIG} не найден")
        return False

    src = CONFIG.read_text(encoding="utf-8")
    if MARKER_CONFIG in src:
        print("  уже пропатчен — пропуск")
        return True

    if CONFIG_ANCHOR not in src:
        print(f"  [FATAL] Якорь не найден: {CONFIG_ANCHOR!r}")
        return False

    _backup(CONFIG, ".minespd.bak")

    # Вставляем новый блок после SATOSHI = 10 ** DECIMALS
    # (найдём конец строки и вставим сразу после)
    idx = src.find(CONFIG_ANCHOR)
    line_end = src.find("\n", idx)
    new_src = src[:line_end + 1] + CONFIG_ADD + src[line_end + 1:]

    CONFIG.write_text(new_src, encoding="utf-8")
    print("  добавлены MINE_SAVE_EVERY_N_BLOCKS=1, MINE_BROADCAST=True")
    return True


def patch_server_file() -> bool:
    print(f"[network/server.py]")
    if not SERVER.exists():
        print(f"  [FATAL] {SERVER} не найден")
        return False

    src = SERVER.read_text(encoding="utf-8")
    if MARKER_SERVER in src:
        print("  уже пропатчен — пропуск")
        return True

    _backup(SERVER, ".minespd.bak")

    src = _replace_once(src, MINE_SAVE_OLD, MINE_SAVE_NEW, "/mine save")
    print("  /mine — условное сохранение + опциональная рассылка")

    src = _replace_once(src, LIFESPAN_ANCHOR, LIFESPAN_NEW, "lifespan shutdown save")
    print("  lifespan — финальный save при shutdown")

    SERVER.write_text(src, encoding="utf-8")
    return True


def main() -> int:
    print("=" * 60)
    print("  AIX OS — ускорение майнинга")
    print("=" * 60)
    print()

    ok1 = patch_config_file()
    print()
    ok2 = patch_server_file()
    print()

    if not (ok1 and ok2):
        print("[FAIL] Что-то не пропатчилось. Проверь *.minespd.bak.")
        return 1

    print("=" * 60)
    print("  Готово")
    print("=" * 60)
    print()
    print("Что теперь:")
    print("  • По умолчанию поведение НЕ изменилось (save_every=1, broadcast=True)")
    print("  • Для быстрого майнинга — патч конфига отдельной командой:")
    print()
    print("    .venv\\Scripts\\python.exe scripts\\patch_config.py --mine-save-every 100 --mine-broadcast off")
    print()
    print("  • После майнинга — вернуть обратно:")
    print()
    print("    .venv\\Scripts\\python.exe scripts\\patch_config.py --mine-save-every 1 --mine-broadcast on")
    return 0


if __name__ == "__main__":
    sys.exit(main())