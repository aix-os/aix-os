"""Патч node_client.dart: /tx/submit → /sync/tx, без обёртки {'tx': ...}."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
TARGET = ROOT / "mobile" / "flutter_app" / "lib" / "services" / "node_client.dart"

OLD = '''  Future<Map<String, dynamic>?> submitSignedTransaction(SignedTransaction tx) =>
      _post('/tx/submit', tx.toJson());'''

NEW = '''  Future<Map<String, dynamic>?> submitSignedTransaction(SignedTransaction tx) =>
      _post('/sync/tx', tx.toJson());'''

def main():
    if not TARGET.exists():
        print(f"❌ Не найден: {TARGET}")
        return 1
    text = TARGET.read_text(encoding="utf-8")
    if OLD not in text:
        print("⚠️  Фрагмент не найден — возможно, уже пропатчено")
        return 0
    TARGET.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print(f"✅ Патч применён: {TARGET}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())