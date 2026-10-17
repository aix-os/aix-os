"""Исправление Батча 5: добавляем публичные методы в NodeClient и правим экраны."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
FLUTTER = ROOT / "mobile" / "flutter_app" / "lib"
SCREENS = FLUTTER / "screens"
CLIENT = FLUTTER / "services" / "node_client.dart"

# =============================================================================
# 1. ДОБАВЛЯЕМ МЕТОДЫ В NODE_CLIENT
# =============================================================================
content = CLIENT.read_text(encoding="utf-8")

# Добавляем методы Lottery, Burn, Sync перед методами Brain или в конец
if "getLotteryStats" not in content:
    insert_point = content.find("  // =========================================================================\n  // BRAIN")
    if insert_point == -1:
        insert_point = content.rfind("}") # fallback
    
    new_methods = '''  // =========================================================================
  // LOTTERY
  // =========================================================================

  Future<Map<String, dynamic>?> getLotteryStats() => _get('/lottery/stats');
  Future<Map<String, dynamic>?> getLotteryInfo() => _get('/lottery/info');

  // =========================================================================
  // BURN
  // =========================================================================

  Future<Map<String, dynamic>?> getBurnCatalog() => _get('/burn/catalog');
  Future<Map<String, dynamic>?> getBurnStats() => _get('/burn/stats');
  Future<Map<String, dynamic>?> getBurnByOwner(String address) => _get('/burn/owner/$address');
  
  Future<Map<String, dynamic>?> mintBurn({
    required String address,
    required String level,
  }) => _post('/burn/mint', {'address': address, 'level': level});

  // =========================================================================
  // SYNC
  // =========================================================================

  Future<Map<String, dynamic>?> syncPull() => _post('/sync/pull', {});
  Future<Map<String, dynamic>?> syncStatePull() => _post('/sync/state/pull', {});

'''
    content = content[:insert_point] + new_methods + content[insert_point:]
    CLIENT.write_text(content, encoding="utf-8")
    print("✅ Обновлён node_client.dart (добавлены методы Lottery, Burn, Sync)")
else:
    print("ℹ️ node_client.dart уже содержит нужные методы")

# =============================================================================
# 2. ИСПРАВЛЯЕМ LOTTERY_SCREEN.DART
# =============================================================================
lottery_path = SCREENS / "lottery_screen.dart"
content = lottery_path.read_text(encoding="utf-8")
content = content.replace("active.remote._get('/lottery/stats')", "active.remote.getLotteryStats()")
lottery_path.write_text(content, encoding="utf-8")
print("✅ Исправлен lottery_screen.dart")

# =============================================================================
# 3. ИСПРАВЛЯЕМ BURN_SCREEN.DART
# =============================================================================
burn_path = SCREENS / "burn_screen.dart"
content = burn_path.read_text(encoding="utf-8")

# Заменяем вызовы
content = content.replace("active.remote._get('/burn/catalog')", "active.remote.getBurnCatalog()")
content = content.replace("active.remote.getBurnStats()", "active.remote.getBurnStats()") # Уже есть в плане
content = content.replace("active.remote._get('/burn/owner/$addr')", "active.remote.getBurnByOwner(addr)")
content = content.replace("active.remote._post('/burn/mint', {'address': _address!, 'level': level})", "active.remote.mintBurn(address: _address!, level: level)")

# Фикс парсинга каталога (ключ уровня)
old_parse = """      if (catRes != null && catRes['catalog'] is Map) {
        _catalog = (catRes['catalog'] as Map).values.toList();
      }"""
new_parse = """      if (catRes != null && catRes['catalog'] is Map) {
        _catalog = (catRes['catalog'] as Map).entries.map((e) {
          final data = Map<String, dynamic>.from(e.value as Map);
          data['level'] = e.key;
          return data;
        }).toList();
      }"""
content = content.replace(old_parse, new_parse)

burn_path.write_text(content, encoding="utf-8")
print("✅ Исправлен burn_screen.dart")

# =============================================================================
# 4. ИСПРАВЛЯЕМ SYNC_SCREEN.DART
# =============================================================================
sync_path = SCREENS / "sync_screen.dart"
content = sync_path.read_text(encoding="utf-8")

content = content.replace("active.remote._post('/sync/pull', {})", "active.remote.syncPull()")
content = content.replace("active.remote._post('/sync/state/pull', {})", "active.remote.syncStatePull()")

sync_path.write_text(content, encoding="utf-8")
print("✅ Исправлен sync_screen.dart")

print("\n🎉 Все ошибки исправлены! Нажми R в терминале Flutter.")