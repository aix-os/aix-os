"""Финальное исправление мобилки перед подключением к облаку."""
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent
FLUTTER = ROOT / "mobile" / "flutter_app" / "lib"
ANDROID = ROOT / "mobile" / "flutter_app" / "android"

# 1. Майнинг (делаем цикл)
node_tab = FLUTTER / "screens" / "node_tab.dart"
content = node_tab.read_text(encoding="utf-8")
old_loop = """  Future<void> _loop() async {
    while (_mining && mounted) {
      final res = await widget.service.mine(widget.address!);
      if (!mounted || !_mining) break;
      
      if (res != null) {
        setState(() {
          _blocksMined += 1;
          _earned += res.rewardAix.toDouble();
          _lastHash = res.blockHash;
        });
      }
      
      // Небольшая пауза между блоками, чтобы UI не зависал
      await Future.delayed(const Duration(milliseconds: 100));
    }
  }"""
if old_loop in content:
    content = content.replace(old_loop, """  Future<void> _loop() async {
    while (_mining && mounted) {
      try {
        final res = await widget.service.mine(widget.address!);
        if (!mounted || !_mining) break;
        if (res != null) {
          setState(() { _blocksMined += 1; _earned += res.rewardAix.toDouble(); _lastHash = res.blockHash; });
        }
      } catch (e) {
        _stopMining(); break;
      }
      await Future.delayed(const Duration(milliseconds: 50));
    }
  }""")
    node_tab.write_text(content, encoding="utf-8")

# 2. Обмен (игнорируем -SIM)
swap_tab = FLUTTER / "screens" / "swap_tab.dart"
content = swap_tab.read_text(encoding="utf-8")
old_pool = """      final a = p['token_a'];
      final b = p['token_b'];
      if ((a == _fromToken && b == _toToken) ||
          (a == _toToken && b == _fromToken)) {"""
new_pool = """      final a = p['token_a'].toString().replaceAll('-SIM', '');
      final b = p['token_b'].toString().replaceAll('-SIM', '');
      final from = _fromToken!.replaceAll('-SIM', '');
      final to = _toToken!.replaceAll('-SIM', '');
      if ((a == from && b == to) || (a == to && b == from)) {"""
if old_pool in content:
    content = content.replace(old_pool, new_pool)
    swap_tab.write_text(content, encoding="utf-8")

# 3. Сканер (разрешения)
manifest = ANDROID / "app" / "src" / "main" / "AndroidManifest.xml"
content = manifest.read_text(encoding="utf-8")
if "android.hardware.camera" not in content:
    content = content.replace(
        '<uses-permission android:name="android.permission.CAMERA"/>',
        '<uses-permission android:name="android.permission.CAMERA"/>\n    <uses-feature android:name="android.hardware.camera" android:required="false" />'
    )
    manifest.write_text(content, encoding="utf-8")

print("✅ Все фиксы применены! Теперь запусти сборку: python scripts\\build_apk.py")