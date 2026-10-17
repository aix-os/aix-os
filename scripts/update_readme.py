"""Обновление README.md перед публикацией."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
README = ROOT / "README.md"

content = README.read_text(encoding="utf-8")

# Обновляем цифры
content = content.replace("21 000 000 max", "21 000 000 000 max")
content = content.replace("52 tests passing", "58 tests passing")
content = content.replace("- ✅ 12 protocols implemented", "- ✅ 12 protocols implemented in mobile UI")
content = content.replace("- ✅ Brain Web UI (#AI-4) — chat in browser (read-only)", "- ✅ Brain Mobile UI — full chat in Flutter")
content = content.replace("🟡 Landing page v2 (live stats + demo)", "✅ Live CoinGecko prices (BTC, ETH, etc.)")
content = content.replace("📋 ZK proofs, LoRa mesh, Flutter Android APK", "🚧 ZK proofs, LoRa mesh, Flutter Android APK")

# Добавляем блок про мобильное приложение
mobile_block = """
## 📱 Mobile App (Flutter)

The mobile wallet is fully functional and includes:
- **Local Node** — mine, send, and sync blocks offline.
- **AIX Brain** — local LLM (Ollama) right in your pocket.
- **Messenger** — send text messages via blockchain transactions.
- **Live Prices** — real-time crypto rates via CoinGecko API.
- **12 Protocols** — DAO, Gifts, TimeLock, Swap, Contacts, Medals, and more.
"""

if "## 📱 Mobile App (Flutter)" not in content:
    content = content.replace("## 🛠 Tech stack", mobile_block + "\n## 🛠 Tech stack")

README.write_text(content, encoding="utf-8")
print("✅ README.md обновлён и готов к публикации!")