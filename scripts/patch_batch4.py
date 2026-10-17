"""Патч Батча 4: DAO, Подарки, TimeLock."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
FLUTTER = ROOT / "mobile" / "flutter_app" / "lib"
SCREENS = FLUTTER / "screens"

# =============================================================================
# 1. DAO SCREEN
# =============================================================================
dao_code = r'''/// AIX OS — DAO (Голосование).
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/wallet_service.dart';
import '../theme.dart';

class DaoScreen extends StatefulWidget {
  const DaoScreen({super.key});
  @override
  State<DaoScreen> createState() => _DaoScreenState();
}

class _DaoScreenState extends State<DaoScreen> {
  List<dynamic> _proposals = [];
  Map<String, dynamic>? _stats;
  String? _address;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final active = context.read<ActiveNodeService>();
    if (active.isLocal) { setState(() => _loading = false); return; }

    final svc = context.read<WalletService>();
    final addr = await svc.getWalletAddress();
    final stats = await active.remote.getDaoStats();
    final list = await active.remote.getDaoAll(limit: 50);

    if (!mounted) return;
    setState(() {
      _address = addr;
      _stats = stats;
      _proposals = (list?['proposals'] as List?) ?? [];
      _loading = false;
    });
  }

  Future<void> _vote(String id, String choice) async {
    if (_address == null) return;
    final active = context.read<ActiveNodeService>();
    final res = await active.remote.voteDao(proposalId: id, voter: _address!, choice: choice);
    if (!mounted) return;
    if (res == null || res.containsKey('__error__')) {
      _snack('Ошибка: ${res?['__error__'] ?? 'нет ответа'}');
      return;
    }
    _snack('Голос принят');
    _load();
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), backgroundColor: AixTheme.cosmos2));
  }

  @override
  Widget build(BuildContext context) {
    final active = context.watch<ActiveNodeService>();
    if (active.isLocal) return _localWarning();

    return Scaffold(
      backgroundColor: AixTheme.cosmos,
      appBar: AppBar(title: const Text('DAO'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AixTheme.neon))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_stats != null)
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AixTheme.cosmos2,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(color: AixTheme.neon.withValues(alpha: 0.2)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _stat('Всего', '${_stats!['total'] ?? 0}'),
                          _stat('Активных', '${_stats!['active'] ?? 0}'),
                          _stat('Кворум', '${_stats!['quorum_percent'] ?? 30}%'),
                        ],
                      ),
                    ),
                  const SizedBox(height: 20),
                  const Text('ПРЕДЛОЖЕНИЯ', style: TextStyle(color: AixTheme.muted, fontSize: 11, letterSpacing: 2)),
                  const SizedBox(height: 10),
                  if (_proposals.isEmpty)
                    const Center(child: Text('Нет предложений', style: TextStyle(color: AixTheme.muted)))
                  else
                    ..._proposals.map((p) => _proposalCard(p)),
                ],
              ),
            ),
    );
  }

  Widget _stat(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(color: AixTheme.gold, fontSize: 18, fontWeight: FontWeight.w800)),
        Text(label, style: const TextStyle(color: AixTheme.muted, fontSize: 11)),
      ],
    );
  }

  Widget _proposalCard(Map<String, dynamic> p) {
    final status = p['status'] ?? 'pending';
    final isActive = status == 'voting' || status == 'pending';
    final title = p['title'] ?? 'Без названия';
    final desc = p['description'] ?? '';
    final id = p['id'] ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AixTheme.cosmos2,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: isActive ? AixTheme.neon.withValues(alpha: 0.3) : AixTheme.muted.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(id, style: const TextStyle(color: AixTheme.muted, fontSize: 11, fontFamily: 'monospace')),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: isActive ? AixTheme.green.withValues(alpha: 0.15) : AixTheme.muted.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(status.toUpperCase(), style: TextStyle(color: isActive ? AixTheme.green : AixTheme.muted, fontSize: 10, fontWeight: FontWeight.w800)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(title, style: const TextStyle(color: AixTheme.text, fontSize: 15, fontWeight: FontWeight.w700)),
          if (desc.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(desc, style: const TextStyle(color: AixTheme.muted, fontSize: 12), maxLines: 2, overflow: TextOverflow.ellipsis),
          ],
          if (isActive) ...[
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _vote(id, 'yes'),
                    style: OutlinedButton.styleFrom(foregroundColor: AixTheme.green, side: const BorderSide(color: AixTheme.green)),
                    child: const Text('ЗА'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => _vote(id, 'no'),
                    style: OutlinedButton.styleFrom(foregroundColor: AixTheme.red, side: const BorderSide(color: AixTheme.red)),
                    child: const Text('ПРОТИВ'),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _localWarning() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.dns_outlined, color: AixTheme.amber, size: 60),
            const SizedBox(height: 16),
            const Text('DAO недоступен\nв автономном режиме', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            const Text('Переключись на Внешнюю ноду', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.muted, fontSize: 13)),
          ],
        ),
      ),
    );
  }
}
'''

# =============================================================================
# 2. GIFTS SCREEN
# =============================================================================
gifts_code = r'''/// AIX OS — Подарки (Gift-Link).
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/wallet_service.dart';
import '../theme.dart';

class GiftsScreen extends StatefulWidget {
  const GiftsScreen({super.key});
  @override
  State<GiftsScreen> createState() => _GiftsScreenState();
}

class _GiftsScreenState extends State<GiftsScreen> {
  final _amountCtrl = TextEditingController();
  final _claimCtrl = TextEditingController();
  List<dynamic> _myGifts = [];
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
    _amountCtrl.dispose();
    _claimCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final active = context.read<ActiveNodeService>();
    if (active.isLocal) { setState(() => _loading = false); return; }

    final svc = context.read<WalletService>();
    final addr = await svc.getWalletAddress();
    if (!mounted) return;
    setState(() => _address = addr);

    if (addr != null) {
      final res = await active.remote.listGiftsBySender(addr);
      if (!mounted) return;
      setState(() {
        _myGifts = (res?['links'] as List?) ?? [];
        _loading = false;
      });
    } else {
      setState(() => _loading = false);
    }
  }

  Future<void> _createGift() async {
    if (_address == null) return;
    final amount = double.tryParse(_amountCtrl.text.replaceAll(',', '.'));
    if (amount == null || amount <= 0) return;

    setState(() => _busy = true);
    final active = context.read<ActiveNodeService>();
    final res = await active.remote.createGift(sender: _address!, amountAix: amount);
    if (!mounted) return;
    setState(() => _busy = false);

    if (res == null || res.containsKey('__error__')) {
      _snack('Ошибка: ${res?['__error__'] ?? 'нет ответа'}');
      return;
    }
    _snack('Создана ссылка: ${res['code']}');
    _amountCtrl.clear();
    _load();
  }

  Future<void> _claimGift() async {
    final code = _claimCtrl.text.trim().toUpperCase();
    if (code.isEmpty || _address == null) return;

    setState(() => _busy = true);
    final active = context.read<ActiveNodeService>();
    final res = await active.remote.claimGift(code: code, recipient: _address!);
    if (!mounted) return;
    setState(() => _busy = false);

    if (res == null || res.containsKey('__error__')) {
      _snack('Ошибка: ${res?['__error__'] ?? 'нет ответа'}');
      return;
    }
    _snack('Подарок получен!');
    _claimCtrl.clear();
    _load();
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), backgroundColor: AixTheme.cosmos2));
  }

  @override
  Widget build(BuildContext context) {
    final active = context.watch<ActiveNodeService>();
    if (active.isLocal) return _localWarning();

    return Scaffold(
      backgroundColor: AixTheme.cosmos,
      appBar: AppBar(title: const Text('Подарки'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AixTheme.neon))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _card(
                    title: 'Создать Gift-Link',
                    children: [
                      TextField(
                        controller: _amountCtrl,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        style: const TextStyle(color: AixTheme.text),
                        decoration: _dec('Сумма AIX'),
                      ),
                      const SizedBox(height: 14),
                      FilledButton(
                        onPressed: _busy ? null : _createGift,
                        style: FilledButton.styleFrom(backgroundColor: AixTheme.purple, padding: const EdgeInsets.symmetric(vertical: 14)),
                        child: const Text('Создать ссылку', style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _card(
                    title: 'Активировать код',
                    children: [
                      TextField(
                        controller: _claimCtrl,
                        style: const TextStyle(color: AixTheme.text, fontFamily: 'monospace'),
                        decoration: _dec('AIX-XXXX-XXXX'),
                      ),
                      const SizedBox(height: 14),
                      OutlinedButton(
                        onPressed: _busy ? null : _claimGift,
                        style: OutlinedButton.styleFrom(foregroundColor: AixTheme.neon, side: const BorderSide(color: AixTheme.neon), padding: const EdgeInsets.symmetric(vertical: 14)),
                        child: const Text('Забрать', style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _card(
                    title: 'Мои подарки (${_myGifts.length})',
                    children: _myGifts.isEmpty
                        ? [const Text('Пока пусто', style: TextStyle(color: AixTheme.muted, fontSize: 13))]
                        : _myGifts.map((g) => _giftRow(g)).toList(),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _giftRow(Map<String, dynamic> g) {
    final code = g['code'] ?? '?';
    final amount = (g['amount_aix'] as num?)?.toStringAsFixed(2) ?? '?';
    final status = g['status'] ?? 'active';
    final isActive = status == 'active';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(code, style: const TextStyle(color: AixTheme.text, fontFamily: 'monospace', fontWeight: FontWeight.w700)),
              Text('$amount AIX', style: const TextStyle(color: AixTheme.muted, fontSize: 12)),
            ],
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: isActive ? AixTheme.green.withValues(alpha: 0.15) : AixTheme.muted.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(status.toUpperCase(), style: TextStyle(color: isActive ? AixTheme.green : AixTheme.muted, fontSize: 10, fontWeight: FontWeight.w800)),
          ),
        ],
      ),
    );
  }

  Widget _card({required String title, required List<Widget> children}) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AixTheme.cosmos2,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AixTheme.neon.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: const TextStyle(color: AixTheme.gold, fontSize: 14, fontWeight: FontWeight.w700, letterSpacing: 1)),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AixTheme.muted),
        filled: true,
        fillColor: AixTheme.cosmos,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: AixTheme.neon.withValues(alpha: 0.3))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: AixTheme.neon.withValues(alpha: 0.3))),
      );

  Widget _localWarning() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.dns_outlined, color: AixTheme.amber, size: 60),
            const SizedBox(height: 16),
            const Text('Подарки недоступны\nв автономном режиме', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            const Text('Переключись на Внешнюю ноду', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.muted, fontSize: 13)),
          ],
        ),
      ),
    );
  }
}
'''

# =============================================================================
# 3. TIMELOCK SCREEN
# =============================================================================
timelock_code = r'''/// AIX OS — Капсулы времени (TimeLock).
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/wallet_service.dart';
import '../theme.dart';

class TimeLockScreen extends StatefulWidget {
  const TimeLockScreen({super.key});
  @override
  State<TimeLockScreen> createState() => _TimeLockScreenState();
}

class _TimeLockScreenState extends State<TimeLockScreen> {
  final _amountCtrl = TextEditingController();
  final _dateCtrl = TextEditingController();
  List<dynamic> _myLocks = [];
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
    _amountCtrl.dispose();
    _dateCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final active = context.read<ActiveNodeService>();
    if (active.isLocal) { setState(() => _loading = false); return; }

    final svc = context.read<WalletService>();
    final addr = await svc.getWalletAddress();
    if (!mounted) return;
    setState(() => _address = addr);

    if (addr != null) {
      final res = await active.remote.listTimeLocksByOwner(addr);
      if (!mounted) return;
      setState(() {
        _myLocks = (res?['locks'] as List?) ?? [];
        _loading = false;
      });
    } else {
      setState(() => _loading = false);
    }
  }

  Future<void> _createLock() async {
    if (_address == null) return;
    final amount = double.tryParse(_amountCtrl.text.replaceAll(',', '.'));
    final date = _dateCtrl.text.trim();
    if (amount == null || amount <= 0 || date.isEmpty) return;

    setState(() => _busy = true);
    final active = context.read<ActiveNodeService>();
    final res = await active.remote.createTimeLock(owner: _address!, amountAix: amount, until: date);
    if (!mounted) return;
    setState(() => _busy = false);

    if (res == null || res.containsKey('__error__')) {
      _snack('Ошибка: ${res?['__error__'] ?? 'нет ответа'}');
      return;
    }
    _snack('Капсула создана до ${res['unlock_at']}');
    _amountCtrl.clear();
    _dateCtrl.clear();
    _load();
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg), backgroundColor: AixTheme.cosmos2));
  }

  @override
  Widget build(BuildContext context) {
    final active = context.watch<ActiveNodeService>();
    if (active.isLocal) return _localWarning();

    return Scaffold(
      backgroundColor: AixTheme.cosmos,
      appBar: AppBar(title: const Text('Капсулы времени'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AixTheme.neon))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _card(
                    title: 'Создать капсулу',
                    children: [
                      TextField(
                        controller: _amountCtrl,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        style: const TextStyle(color: AixTheme.text),
                        decoration: _dec('Сумма AIX'),
                      ),
                      const SizedBox(height: 14),
                      TextField(
                        controller: _dateCtrl,
                        style: const TextStyle(color: AixTheme.text),
                        decoration: _dec('До какой даты (YYYY-MM-DD)'),
                      ),
                      const SizedBox(height: 14),
                      FilledButton(
                        onPressed: _busy ? null : _createLock,
                        style: FilledButton.styleFrom(backgroundColor: AixTheme.purple, padding: const EdgeInsets.symmetric(vertical: 14)),
                        child: const Text('Создать', style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _card(
                    title: 'Мои капсулы (${_myLocks.length})',
                    children: _myLocks.isEmpty
                        ? [const Text('Пока пусто', style: TextStyle(color: AixTheme.muted, fontSize: 13))]
                        : _myLocks.map((l) => _lockRow(l)).toList(),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _lockRow(Map<String, dynamic> l) {
    final id = l['id'] ?? '?';
    final amount = (l['amount_aix'] as num?)?.toStringAsFixed(2) ?? '?';
    final status = l['status'] ?? 'locked';
    final timeLeft = l['time_left'] ?? '—';
    final isUnlockable = status == 'unlockable';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(id, style: const TextStyle(color: AixTheme.text, fontFamily: 'monospace', fontWeight: FontWeight.w700)),
              Text('$amount AIX', style: const TextStyle(color: AixTheme.muted, fontSize: 12)),
            ],
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: isUnlockable ? AixTheme.green.withValues(alpha: 0.15) : AixTheme.gold.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(status.toUpperCase(), style: TextStyle(color: isUnlockable ? AixTheme.green : AixTheme.gold, fontSize: 10, fontWeight: FontWeight.w800)),
              ),
              const SizedBox(height: 2),
              Text(timeLeft, style: const TextStyle(color: AixTheme.muted, fontSize: 11)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _card({required String title, required List<Widget> children}) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AixTheme.cosmos2,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AixTheme.neon.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: const TextStyle(color: AixTheme.gold, fontSize: 14, fontWeight: FontWeight.w700, letterSpacing: 1)),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AixTheme.muted),
        filled: true,
        fillColor: AixTheme.cosmos,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: AixTheme.neon.withValues(alpha: 0.3))),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide(color: AixTheme.neon.withValues(alpha: 0.3))),
      );

  Widget _localWarning() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(30),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.dns_outlined, color: AixTheme.amber, size: 60),
            const SizedBox(height: 16),
            const Text('Капсулы времени недоступны\nв автономном режиме', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 12),
            const Text('Переключись на Внешнюю ноду', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.muted, fontSize: 13)),
          ],
        ),
      ),
    );
  }
}
'''

# =============================================================================
# ЗАПИСЬ ФАЙЛОВ
# =============================================================================
(SCREENS / "dao_screen.dart").write_text(dao_code, encoding="utf-8")
print("✅ Создан dao_screen.dart")

(SCREENS / "gifts_screen.dart").write_text(gifts_code, encoding="utf-8")
print("✅ Создан gifts_screen.dart")

(SCREENS / "timelock_screen.dart").write_text(timelock_code, encoding="utf-8")
print("✅ Создан timelock_screen.dart")

# =============================================================================
# ПАТЧ MAIN.DART
# =============================================================================
main_dart = FLUTTER / "main.dart"
content = main_dart.read_text(encoding="utf-8")

# 1. Добавляем импорты
if "dao_screen.dart" not in content:
    content = content.replace(
        "import 'screens/poc_screen.dart';",
        "import 'screens/poc_screen.dart';\nimport 'screens/dao_screen.dart';\nimport 'screens/gifts_screen.dart';\nimport 'screens/timelock_screen.dart';"
    )

# 2. Заменяем маршруты
content = content.replace(
    "          '/dao': (context) => const PlaceholderScreen(\n                title: 'DAO',\n                emoji: '🗳',\n                description: 'Голосование. Скоро в батче 4.',\n              ),",
    "          '/dao': (context) => const DaoScreen(),"
)
content = content.replace(
    "          '/gifts': (context) => const PlaceholderScreen(\n                title: 'Подарки',\n                emoji: '🎁',\n                description: 'Gift-ссылки. Скоро в батче 4.',\n              ),",
    "          '/gifts': (context) => const GiftsScreen(),"
)
content = content.replace(
    "          '/timelock': (context) => const PlaceholderScreen(\n                title: 'Капсулы времени',\n                emoji: '🕰',\n                description: 'TimeLock. Скоро в батче 4.',\n              ),",
    "          '/timelock': (context) => const TimeLockScreen(),"
)

main_dart.write_text(content, encoding="utf-8")
print("✅ Обновлён main.dart (маршруты DAO, Gifts, TimeLock)")

print("\n🎉 Батч 4 готов! Нажми R в терминале Flutter.")