"""Увеличение таймаута для AIX Brain в мобильном клиенте."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
CLIENT = ROOT / "mobile" / "flutter_app" / "lib" / "services" / "node_client.dart"

content = CLIENT.read_text(encoding="utf-8")

# 1. Меняем сигнатуру метода _post, чтобы принимать timeoutSeconds
old_post_sig = """  Future<Map<String, dynamic>?> _post(
      String path, Map<String, dynamic> body) async {
    try {
      final r = await http
          .post(
            Uri.parse('$_nodeUrl$path'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 30));"""

new_post_sig = """  Future<Map<String, dynamic>?> _post(
      String path, Map<String, dynamic> body, {int timeoutSeconds = 30}) async {
    try {
      final r = await http
          .post(
            Uri.parse('$_nodeUrl$path'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(Duration(seconds: timeoutSeconds));"""

if old_post_sig in content:
    content = content.replace(old_post_sig, new_post_sig)

# 2. Меняем вызов brainAsk, чтобы он ждал 3 минуты (180 секунд)
old_brain = """  Future<Map<String, dynamic>?> brainAsk(String message) =>
      _post('/brain/ask', {'message': message});"""

new_brain = """  Future<Map<String, dynamic>?> brainAsk(String message) =>
      _post('/brain/ask', {'message': message}, timeoutSeconds: 180);"""

if old_brain in content:
    content = content.replace(old_brain, new_brain)

CLIENT.write_text(content, encoding="utf-8")
print("✅ node_client.dart обновлён: таймаут для Brain теперь 180 секунд.")