"""Финальный патч: Сжигание с ключом, защита Brain, Мессенджер."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
FLUTTER = ROOT / "mobile" / "flutter_app" / "lib"
SCREENS = FLUTTER / "screens"

# =============================================================================
# 1. ПАТЧ PYTHON: BURN_TO_MINT.PY (принимаем ключ)
# =============================================================================
burn_py = ROOT / "core" / "protocols" / "burn_to_mint.py"
content = burn_py.read_text(encoding="utf-8")

# Меняем функцию mint, чтобы она принимала private_key
if "def mint(self, owner: str, level: str, private_key: str = \"\"," not in content:
    content = content.replace(
        "def mint(self, owner: str, level: str,\n             blockchain=None) -> tuple[bool, str, Optional[BurnArtifact]]:",
        "def mint(self, owner: str, level: str, private_key: str = \"\",\n             blockchain=None) -> tuple[bool, str, Optional[BurnArtifact]]:"
    )
    
    # Заменяем поиск локального кошелька на использование переданного ключа
    old_wallet_logic = """        owner_wallet = self._find_wallet(owner)
        if owner_wallet is None:
            return False, "Локальный кошелёк не найден", None"""

    new_wallet_logic = """        import ecdsa
        if private_key:
            sk = ecdsa.SigningKey.from_string(bytes.fromhex(private_key), curve=ecdsa.SECP256k1)
        else:
            owner_wallet = self._find_wallet(owner)
            if owner_wallet is None:
                return False, "Локальный кошелёк не найден", None
            sk = owner_wallet.get_signing_key()"""
    
    content = content.replace(old_wallet_logic, new_wallet_logic)
    content = content.replace("owner_wallet.sign_transaction(tx)", "tx.sign_transaction(sk)")
    burn_py.write_text(content, encoding="utf-8")
    print("✅ Обновлён burn_to_mint.py")

# =============================================================================
# 2. ПАТЧ PYTHON: SERVER.PY (передаём ключ)
# =============================================================================
server_py = ROOT / "network" / "server.py"
content = server_py.read_text(encoding="utf-8")

# Добавляем поле private_key в модель BurnMintRequest
if "class BurnMintRequest(BaseModel):\n    address: str\n    level: str" in content:
    content = content.replace(
        "class BurnMintRequest(BaseModel):\n    address: str\n    level: str",
        "class BurnMintRequest(BaseModel):\n    address: str\n    level: str\n    private_key: str = \"\""
    )

# Передаём ключ в менеджер
if "ok, msg, artifact = burn_manager.mint(\n            owner=owner_addr, level=req.level, blockchain=blockchain,\n        )" in content:
    content = content.replace(
        "ok, msg, artifact = burn_manager.mint(\n            owner=owner_addr, level=req.level, blockchain=blockchain,\n        )",
        "ok, msg, artifact = burn_manager.mint(\n            owner=owner_addr, level=req.level, private_key=req.private_key, blockchain=blockchain,\n        )"
    )
server_py.write_text(content, encoding="utf-8")
print("✅ Обновлён server.py")

# =============================================================================
# 3. ПАТЧ FLUTTER: NODE_CLIENT.DART (передаём ключ при сжигании)
# =============================================================================
client_dart = FLUTTER / "services" / "node_client.dart"
content = client_dart.read_text(encoding="utf-8")

if "mintBurn({" in content:
    content = content.replace(
        "Future<Map<String, dynamic>?> mintBurn({\n    required String address,\n    required String level,\n  }) => _post('/burn/mint', {'address': address, 'level': level});",
        "Future<Map<String, dynamic>?> mintBurn({\n    required String address,\n    required String level,\n    required String privateKey,\n  }) => _post('/burn/mint', {'address': address, 'level': level, 'private_key': privateKey});"
    )
client_dart.write_text(content, encoding="utf-8")
print("✅ Обновлён node_client.dart")

# =============================================================================
# 4. ПАТЧ FLUTTER: BURN_SCREEN.DART (берём ключ из кошелька)
# =============================================================================
burn_screen = SCREENS / "burn_screen.dart"
content = burn_screen.read_text(encoding="utf-8")

if "active.remote.mintBurn(address: _address!, level: level)" in content:
    content = content.replace(
        "final active = context.read<ActiveNodeService>();\n    final res = await active.remote.mintBurn(address: _address!, level: level);",
        "final svc = context.read<WalletService>();\n    final privKey = await svc.getPrivateKeyHex();\n    if (privKey == null) {\n      _snack('Кошелёк не найден');\n      setState(() => _busy = false);\n      return;\n    }\n    final active = context.read<ActiveNodeService>();\n    final res = await active.remote.mintBurn(address: _address!, level: level, privateKey: privKey);"
    )
    burn_screen.write_text(content, encoding="utf-8")
    print("✅ Обновлён burn_screen.dart")

# =============================================================================
# 5. НОВЫЙ ЭКРАН: MESSENGER_SCREEN.DART
# =============================================================================
messenger_code = r'''/// AIX OS — Встроенный мессенджер (чат на транзакциях).
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/wallet_service.dart';
import '../theme.dart';

class MessengerScreen extends StatefulWidget {
  const MessengerScreen({super.key});
  @override
  State<MessengerScreen> createState() => _MessengerScreenState();
}

class _MessengerScreenState extends State<MessengerScreen> {
  final _msgCtrl = TextEditingController();
  final _recipientCtrl = TextEditingController(text: 'AIXTYTXqm8WBFE6iX9UCFsp3qbF3VoKjAMxG8'); // по умолчанию майнер
  final _scrollCtrl = ScrollController();
  List<Map<String, dynamic>> _messages = [];
  String? _address;
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    _msgCtrl.dispose();
    _recipientCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final svc = context.read<WalletService>();
    final addr = await svc.getWalletAddress();
    if (!mounted) return;
    setState(() => _address = addr);

    final active = context.read<ActiveNodeService>();
    final chain = await active.historyOf(addr ?? '');

    if (!mounted) return;
    // Фильтруем только транзакции с сообщениями
    final chat = chain.where((t) => (t['message'] ?? '').toString().isNotEmpty).toList();
    setState(() {
      _messages = chat.reversed.toList();
      _loading = false;
    });
    _scrollToBottom();
  }

  Future<void> _send() async {
    final text = _msgCtrl.text.trim();
    final recipient = _recipientCtrl.text.trim();
    if (text.isEmpty || recipient.isEmpty || _address == null) return;

    setState(() => _busy = true);
    final svc = context.read<WalletService>();
    final privKey = await svc.getPrivateKeyHex();
    if (privKey == null) {
      setState(() => _busy = false);
      return;
    }

    final active = context.read<ActiveNodeService>();
    // Отправляем как обычную транзакцию 0.00000001 AIX с текстом
    final (ok, res) = await active.sendAix(
      privHex: privKey,
      sender: _address!,
      recipient: recipient,
      amountAix: 0.00000001,
      message: text,
    );

    if (!mounted) return;
    setState(() => _busy = false);

    if (ok) {
      _msgCtrl.clear();
      _load(); // Перезагружаем историю
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Ошибка: $res'), backgroundColor: AixTheme.red));
    }
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(_scrollCtrl.position.maxScrollExtent, duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AixTheme.cosmos,
      appBar: AppBar(
        title: const Text('Мессенджер'),
        backgroundColor: AixTheme.cosmos2,
        foregroundColor: AixTheme.gold,
      ),
      body: Column(
        children: [
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator(color: AixTheme.neon))
                : _messages.isEmpty
                    ? const Center(child: Text('Нет сообщений', style: TextStyle(color: AixTheme.muted)))
                    : ListView.builder(
                        controller: _scrollCtrl,
                        padding: const EdgeInsets.all(16),
                        itemCount: _messages.length,
                        itemBuilder: (_, i) {
                          final m = _messages[i];
                          final isMe = m['sender'] == _address;
                          return _messageBubble(m, isMe);
                        },
                      ),
          ),
          if (_busy) const LinearProgressIndicator(color: AixTheme.neon),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: const BoxDecoration(color: AixTheme.cosmos2),
            child: SafeArea(
              top: false,
              child: Column(
                children: [
                  TextField(
                    controller: _recipientCtrl,
                    style: const TextStyle(color: AixTheme.text, fontSize: 12, fontFamily: 'monospace'),
                    decoration: const InputDecoration(
                      hintText: 'AIX-адрес получателя',
                      hintStyle: TextStyle(color: AixTheme.muted),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      isDense: true,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _msgCtrl,
                          style: const TextStyle(color: AixTheme.text),
                          decoration: InputDecoration(
                            hintText: 'Сообщение...',
                            hintStyle: const TextStyle(color: AixTheme.muted),
                            filled: true,
                            fillColor: AixTheme.cosmos,
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                          ),
                          onSubmitted: (_) => _send(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      CircleAvatar(
                        backgroundColor: AixTheme.neon,
                        child: IconButton(
                          icon: const Icon(Icons.send, color: AixTheme.cosmos),
                          onPressed: _busy ? null : _send,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _messageBubble(Map<String, dynamic> m, bool isMe) {
    final text = m['message'] ?? '';
    final time = (m['timestamp'] as num?)?.toDouble() ?? 0;
    final dt = DateTime.fromMillisecondsSinceEpoch((time * 1000).toInt());
    final timeStr = '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';

    return Align(
      alignment: isMe ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isMe ? AixTheme.purple.withValues(alpha: 0.3) : AixTheme.cosmos2,
          borderRadius: BorderRadius.circular(16).copyWith(
            bottomRight: isMe ? Radius.zero : const Radius.circular(16),
            bottomLeft: !isMe ? Radius.zero : const Radius.circular(16),
          ),
          border: Border.all(color: isMe ? AixTheme.purple.withValues(alpha: 0.5) : AixTheme.neon.withValues(alpha: 0.2)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(text, style: const TextStyle(color: AixTheme.text, fontSize: 14)),
            const SizedBox(height: 4),
            Text(timeStr, style: const TextStyle(color: AixTheme.muted, fontSize: 10, fontFamily: 'monospace')),
          ],
        ),
      ),
    );
  }
}
'''
(SCREENS / "messenger_screen.dart").write_text(messenger_code, encoding="utf-8")
print("✅ Создан messenger_screen.dart")

# =============================================================================
# 6. ПАТЧ MAIN.DART (маршрут мессенджера)
# =============================================================================
main_dart = FLUTTER / "main.dart"
content = main_dart.read_text(encoding="utf-8")
if "messenger_screen.dart" not in content:
    content = content.replace(
        "import 'screens/brain_screen.dart';",
        "import 'screens/brain_screen.dart';\nimport 'screens/messenger_screen.dart';"
    )
    content = content.replace(
        "          '/brain': (context) => const BrainScreen(),",
        "          '/brain': (context) => const BrainScreen(),\n          '/messenger': (context) => const MessengerScreen(),"
    )
    main_dart.write_text(content, encoding="utf-8")
    print("✅ Обновлён main.dart (маршрут /messenger)")

# =============================================================================
# 7. ПАТЧ MORE_TAB.DART (добавляем Мессенджер)
# =============================================================================
more_dart = FLUTTER / "screens" / "more_tab.dart"
content = more_dart.read_text(encoding="utf-8")
if "Мессенджер" not in content:
    content = content.replace(
        "      _MoreItem('История', Icons.history_rounded, 'Все транзакции', '/history'),",
        "      _MoreItem('Мессенджер', Icons.chat_bubble_outline_rounded, 'Чат на блокчейне', '/messenger'),\n      _MoreItem('История', Icons.history_rounded, 'Все транзакции', '/history'),"
    )
    more_dart.write_text(content, encoding="utf-8")
    print("✅ Обновлён more_tab.dart (добавлен Мессенджер)")

print("\n🎉 Всё готово! Не забудь перезапустить Python-ноды для применения патча сжигания.")