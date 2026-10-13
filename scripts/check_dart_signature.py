"""
Проверка: подпись из Dart принимается Python-валидатором.

Читает mobile/flutter_app/e2e_out/signed_tx.json, восстанавливает
Transaction, вызывает is_valid().

Запуск:
    .venv\\Scripts\\python.exe scripts\\check_dart_signature.py

Ожидаемый вывод: VALID
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.transaction import Transaction  # noqa: E402


JSON_PATH = ROOT / "mobile" / "flutter_app" / "e2e_out" / "signed_tx.json"


def main() -> int:
    if not JSON_PATH.exists():
        print(f"[FATAL] Файл не найден: {JSON_PATH}")
        print("   Сначала запусти Dart-тест:")
        print("     cd mobile\\flutter_app")
        print("     flutter test test/e2e_sign_test.dart")
        return 1

    raw = JSON_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)

    print("Прочитано из Dart:")
    print(f"  sender:    {data.get('sender')}")
    print(f"  recipient: {data.get('recipient')}")
    print(f"  amount:    {data.get('amount')}")
    print(f"  timestamp: {data.get('timestamp')}  (тип: {type(data.get('timestamp')).__name__})")
    print(f"  fee:       {data.get('fee')}")
    print(f"  message:   {data.get('message')!r}")
    print(f"  public_key: {data.get('public_key', '')[:20]}...")
    print(f"  signature:  {data.get('signature', '')[:20]}...")
    print()

    try:
        tx = Transaction.from_dict(data)
    except Exception as e:
        print(f"[FATAL] Не удалось собрать Transaction: {e}")
        return 1

    ok, msg = tx.is_valid()
    print(f"is_valid(): {ok}  -- {msg}")

    # Сравним tx_id — он должен совпасть с тем, что дал Dart
    if ok:
        tx_id_py = tx.tx_id()
        print(f"tx_id (Python): {tx_id_py}")
        print()
        print("VALID")
        return 0
    else:
        print()
        print(f"INVALID: {msg}")
        return 2


if __name__ == "__main__":
    sys.exit(main())