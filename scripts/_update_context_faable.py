from pathlib import Path
p = Path("CONTEXT.md")
c = p.read_text(encoding="utf-8")

entry = """### 2026-10-18 (сессия 7 — Faable Cloud Node Fixed)

- **OOM на Faable побеждён:** Удалён 68 МБ `chain_A.json` из Git. Облачная нода стартует с `height=0` (генезис), чтобы не превышать лимит RAM. Локальная нода (85k+ блоков) остаётся на ПК.
- **Faable Startup Fixed:** Добавлен `faable.json` (`uvicorn main:app`) и `FAABLE-FALLBACK` в `network/server.py` (создаёт `app` из `PORT`).
- **Faucet Fixed:** Переписан на системный адрес `FAUCET` (в `SYSTEM_SENDERS`). Не требует кошелька `alice`. Выдаёт 1 AIX. Успешно протестирован на Faable: `{"status":"sent","amount_aix":1}`.
- **P2P на облаке:** Эндпоинты `/p2p/*` живы и готовы к UI.
- **Экономика:** Сложность 5, награда 0.005 AIX/блок на Faable.

**Следующий шаг:** Установить новый APK (с текстами 1 AIX и URL Faable) на телефон. Затем — P2P UI.

---

"""

lines = c.split("\n", 1)
new_c = lines[0] + "\n\n" + entry + (lines[1] if len(lines) > 1 else "")
p.write_text(new_c, encoding="utf-8")
print("OK: CONTEXT.md updated")
