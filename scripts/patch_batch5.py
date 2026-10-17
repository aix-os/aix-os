"""Патч Батча 5: Lottery, Inheritance, AIX-ID, Burn, Sync, Brain."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
FLUTTER = ROOT / "mobile" / "flutter_app" / "lib"
SCREENS = FLUTTER / "screens"

# =============================================================================
# 1. LOTTERY SCREEN
# =============================================================================
lottery_code = r'''/// AIX OS — Лотерея.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../theme.dart';

class LotteryScreen extends StatefulWidget {
  const LotteryScreen({super.key});
  @override
  State<LotteryScreen> createState() => _LotteryScreenState();
}

class _LotteryScreenState extends State<LotteryScreen> {
  Map<String, dynamic>? _stats;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final active = context.read<ActiveNodeService>();
    if (active.isLocal) { setState(() => _loading = false); return; }
    final res = await active.remote._get('/lottery/stats');
    if (!mounted) return;
    setState(() { _stats = res; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    final active = context.watch<ActiveNodeService>();
    if (active.isLocal) return _localWarning();

    return Scaffold(
      backgroundColor: AixTheme.cosmos,
      appBar: AppBar(title: const Text('Лотерея'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AixTheme.neon))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (_stats != null) ...[
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        gradient: AixTheme.gradientCard,
                        borderRadius: BorderRadius.circular(AixTheme.radiusL),
                        border: Border.all(color: AixTheme.purple.withValues(alpha: 0.3)),
                      ),
                      child: Column(
                        children: [
                          const Text('ПРИЗОВОЙ ФОНД', style: TextStyle(color: AixTheme.muted, fontSize: 11, letterSpacing: 2)),
                          const SizedBox(height: 8),
                          Text('${_stats!['prize_per_win_aix']} AIX', style: const TextStyle(color: AixTheme.gold, fontSize: 32, fontWeight: FontWeight.w900)),
                          const SizedBox(height: 8),
                          Text('Шанс: ${_stats!['chance']}', style: const TextStyle(color: AixTheme.neon, fontSize: 14, fontWeight: FontWeight.w700)),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),
                    _card(
                      title: 'Статистика',
                      children: [
                        _row('Всего блоков', '${_stats!['total_blocks']}'),
                        _row('Побед', '${_stats!['total_wins']}'),
                        _row('Выплачено', '${(_stats!['total_prize_aix'] as num?)?.toStringAsFixed(2) ?? 0} AIX'),
                      ],
                    ),
                  ],
                ],
              ),
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

  Widget _row(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(k, style: const TextStyle(color: AixTheme.muted, fontSize: 13)),
            Text(v, style: const TextStyle(color: AixTheme.text, fontSize: 13, fontWeight: FontWeight.w700)),
          ],
        ),
      );

  Widget _localWarning() => Center(
        child: Padding(
          padding: const EdgeInsets.all(30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.dns_outlined, color: AixTheme.amber, size: 60),
              const SizedBox(height: 16),
              const Text('Лотерея недоступна\nв автономном режиме', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 12),
              const Text('Переключись на Внешнюю ноду', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.muted, fontSize: 13)),
            ],
          ),
        ),
      );
}
'''

# =============================================================================
# 2. INHERITANCE (DMS) SCREEN
# =============================================================================
inherit_code = r'''/// AIX OS — Наследство (DMS).
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/wallet_service.dart';
import '../theme.dart';

class InheritScreen extends StatefulWidget {
  const InheritScreen({super.key});
  @override
  State<InheritScreen> createState() => _InheritScreenState();
}

class _InheritScreenState extends State<InheritScreen> {
  final _heirsCtrl = TextEditingController();
  final _noteCtrl = TextEditingController();
  List<dynamic> _switches = [];
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
    _heirsCtrl.dispose();
    _noteCtrl.dispose();
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
      final res = await active.remote.listInheritancesByOwner(addr);
      if (!mounted) return;
      setState(() {
        _switches = (res?['switches'] as List?) ?? [];
        _loading = false;
      });
    } else {
      setState(() => _loading = false);
    }
  }

  Future<void> _create() async {
    if (_address == null) return;
    final input = _heirsCtrl.text.trim();
    if (input.isEmpty) return;

    // Формат: "bob:60,carol:40" или "AIX...:100"
    final heirs = <Map<String, dynamic>>[];
    for (final part in input.split(',')) {
      final p = part.trim().split(':');
      if (p.length == 2) {
        heirs.add({'address': p[0].trim(), 'share_percent': double.tryParse(p[1].trim()) ?? 0});
      }
    }
    if (heirs.isEmpty) {
      _snack('Неверный формат. Пример: bob:60,carol:40');
      return;
    }

    setState(() => _busy = true);
    final active = context.read<ActiveNodeService>();
    final res = await active.remote.createInheritance(
      owner: _address!,
      heirs: heirs,
      note: _noteCtrl.text.trim(),
    );
    if (!mounted) return;
    setState(() => _busy = false);

    if (res == null || res.containsKey('__error__')) {
      _snack('Ошибка: ${res?['__error__'] ?? 'нет ответа'}');
      return;
    }
    _snack('Наследство создано');
    _heirsCtrl.clear();
    _noteCtrl.clear();
    _load();
  }

  Future<void> _checkin() async {
    if (_address == null) return;
    final active = context.read<ActiveNodeService>();
    await active.remote.checkinInheritance(_address!);
    _snack('Check-in выполнен');
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
      appBar: AppBar(title: const Text('Наследство'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AixTheme.neon))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _card(
                    title: 'Создать завещание',
                    children: [
                      TextField(
                        controller: _heirsCtrl,
                        style: const TextStyle(color: AixTheme.text),
                        decoration: _dec('bob:60, carol:40 или AIX...:100'),
                      ),
                      const SizedBox(height: 14),
                      TextField(
                        controller: _noteCtrl,
                        style: const TextStyle(color: AixTheme.text),
                        decoration: _dec('Записка для наследников'),
                      ),
                      const SizedBox(height: 14),
                      FilledButton(
                        onPressed: _busy ? null : _create,
                        style: FilledButton.styleFrom(backgroundColor: AixTheme.purple, padding: const EdgeInsets.symmetric(vertical: 14)),
                        child: const Text('Создать', style: TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  _card(
                    title: 'Мои завещания (${_switches.length})',
                    children: [
                      if (_switches.isEmpty)
                        const Text('Пока пусто', style: TextStyle(color: AixTheme.muted, fontSize: 13))
                      else ...[
                        ..._switches.map((s) => _switchRow(s)),
                        const SizedBox(height: 12),
                        OutlinedButton(
                          onPressed: _checkin,
                          style: OutlinedButton.styleFrom(foregroundColor: AixTheme.green, side: const BorderSide(color: AixTheme.green), padding: const EdgeInsets.symmetric(vertical: 14)),
                          child: const Text('Check-in (я жив)', style: TextStyle(fontWeight: FontWeight.w700)),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
    );
  }

  Widget _switchRow(Map<String, dynamic> s) {
    final status = s['status'] ?? 'active';
    final isActive = status == 'active';
    final timeLeft = s['time_left'] ?? '—';
    final heirs = (s['heirs'] as List?) ?? [];

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(s['id'] ?? '?', style: const TextStyle(color: AixTheme.text, fontFamily: 'monospace', fontWeight: FontWeight.w700)),
              Text(isActive ? timeLeft : status.toUpperCase(), style: TextStyle(color: isActive ? AixTheme.gold : AixTheme.red, fontSize: 11, fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 4),
          Text('Наследники: ${heirs.map((h) => "${h['name']}:${h['share_percent']}%").join(", ")}', style: const TextStyle(color: AixTheme.muted, fontSize: 11)),
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

  Widget _localWarning() => Center(
        child: Padding(
          padding: const EdgeInsets.all(30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.dns_outlined, color: AixTheme.amber, size: 60),
              const SizedBox(height: 16),
              const Text('Наследство недоступно\nв автономном режиме', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 12),
              const Text('Переключись на Внешнюю ноду', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.muted, fontSize: 13)),
            ],
          ),
        ),
      );
}
'''

# =============================================================================
# 3. AIX-ID SCREEN
# =============================================================================
aixid_code = r'''/// AIX OS — AIX-ID.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/wallet_service.dart';
import '../theme.dart';

class AixIdScreen extends StatefulWidget {
  const AixIdScreen({super.key});
  @override
  State<AixIdScreen> createState() => _AixIdScreenState();
}

class _AixIdScreenState extends State<AixIdScreen> {
  final _nameCtrl = TextEditingController();
  final _bioCtrl = TextEditingController();
  Map<String, dynamic>? _profile;
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
    _nameCtrl.dispose();
    _bioCtrl.dispose();
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
      final res = await active.remote.getIdProfile(addr);
      if (!mounted) return;
      setState(() {
        _profile = res;
        _loading = false;
      });
    } else {
      setState(() => _loading = false);
    }
  }

  Future<void> _register() async {
    if (_address == null) return;
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) return;

    setState(() => _busy = true);
    final active = context.read<ActiveNodeService>();
    final res = await active.remote.registerId(address: _address!, name: name, bio: _bioCtrl.text.trim());
    if (!mounted) return;
    setState(() => _busy = false);

    if (res == null || res.containsKey('__error__')) {
      _snack('Ошибка: ${res?['__error__'] ?? 'нет ответа'}');
      return;
    }
    _snack('Профиль создан!');
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
      appBar: AppBar(title: const Text('AIX-ID'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AixTheme.neon))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: _profile != null ? _profileCard() : _createCard(),
            ),
    );
  }

  Widget _profileCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: AixTheme.gradientCard,
        borderRadius: BorderRadius.circular(AixTheme.radiusL),
        border: Border.all(color: AixTheme.neon.withValues(alpha: 0.3)),
      ),
      child: Column(
        children: [
          Text(_profile!['avatar'] ?? '👤', style: const TextStyle(fontSize: 60)),
          const SizedBox(height: 12),
          Text('@${_profile!['name']}', style: const TextStyle(color: AixTheme.gold, fontSize: 24, fontWeight: FontWeight.w900)),
          if (_profile!['bio'] != null && _profile!['bio'].toString().isNotEmpty)
            Padding(padding: const EdgeInsets.only(top: 8), child: Text(_profile!['bio'], style: const TextStyle(color: AixTheme.muted, fontSize: 13), textAlign: TextAlign.center)),
          const SizedBox(height: 16),
          const Divider(),
          const SizedBox(height: 8),
          _infoRow('Репутация', '${_profile!['reputation'] ?? 0}'),
          _infoRow('Медалей', '${_profile!['medals_count'] ?? 0}'),
          _infoRow('Баланс', '${(_profile!['balance_aix'] as num?)?.toStringAsFixed(2) ?? 0} AIX'),
        ],
      ),
    );
  }

  Widget _infoRow(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(k, style: const TextStyle(color: AixTheme.muted, fontSize: 13)),
            Text(v, style: const TextStyle(color: AixTheme.text, fontSize: 13, fontWeight: FontWeight.w700)),
          ],
        ),
      );

  Widget _createCard() {
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
          const Text('Создать AIX-ID', style: TextStyle(color: AixTheme.gold, fontSize: 14, fontWeight: FontWeight.w700, letterSpacing: 1)),
          const SizedBox(height: 12),
          TextField(
            controller: _nameCtrl,
            style: const TextStyle(color: AixTheme.text),
            decoration: _dec('Имя (например, alice)'),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _bioCtrl,
            style: const TextStyle(color: AixTheme.text),
            decoration: _dec('О себе (необязательно)'),
          ),
          const SizedBox(height: 14),
          FilledButton(
            onPressed: _busy ? null : _register,
            style: FilledButton.styleFrom(backgroundColor: AixTheme.purple, padding: const EdgeInsets.symmetric(vertical: 14)),
            child: const Text('Зарегистрировать', style: TextStyle(fontWeight: FontWeight.w700)),
          ),
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

  Widget _localWarning() => Center(
        child: Padding(
          padding: const EdgeInsets.all(30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.dns_outlined, color: AixTheme.amber, size: 60),
              const SizedBox(height: 16),
              const Text('AIX-ID недоступен\nв автономном режиме', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 12),
              const Text('Переключись на Внешнюю ноду', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.muted, fontSize: 13)),
            ],
          ),
        ),
      );
}
'''

# =============================================================================
# 4. BURN SCREEN
# =============================================================================
burn_code = r'''/// AIX OS — Сжигание (Burn-to-Mint).
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/wallet_service.dart';
import '../theme.dart';

class BurnScreen extends StatefulWidget {
  const BurnScreen({super.key});
  @override
  State<BurnScreen> createState() => _BurnScreenState();
}

class _BurnScreenState extends State<BurnScreen> {
  List<dynamic> _catalog = [];
  List<dynamic> _myArtifacts = [];
  Map<String, dynamic>? _stats;
  String? _address;
  bool _loading = true;
  bool _busy = false;

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
    if (!mounted) return;
    setState(() => _address = addr);

    final catRes = await active.remote._get('/burn/catalog');
    final statsRes = await active.remote.getBurnStats();
    Map<String, dynamic>? myRes;
    if (addr != null) {
      myRes = await active.remote._get('/burn/owner/$addr');
    }

    if (!mounted) return;
    setState(() {
      if (catRes != null && catRes['catalog'] is Map) {
        _catalog = (catRes['catalog'] as Map).values.toList();
      }
      _stats = statsRes;
      _myArtifacts = (myRes?['artifacts'] as List?) ?? [];
      _loading = false;
    });
  }

  Future<void> _mint(String level) async {
    if (_address == null) return;
    setState(() => _busy = true);
    final active = context.read<ActiveNodeService>();
    final res = await active.remote._post('/burn/mint', {'address': _address!, 'level': level});
    if (!mounted) return;
    setState(() => _busy = false);

    if (res == null || res.containsKey('__error__')) {
      _snack('Ошибка: ${res?['__error__'] ?? 'нет ответа'}');
      return;
    }
    _snack('Артефакт создан!');
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
      appBar: AppBar(title: const Text('Сжигание'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
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
                        border: Border.all(color: AixTheme.red.withValues(alpha: 0.3)),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          Column(
                            children: [
                              Text('${_stats!['total_artifacts'] ?? 0}', style: const TextStyle(color: AixTheme.red, fontSize: 24, fontWeight: FontWeight.w900)),
                              const Text('Артефактов', style: TextStyle(color: AixTheme.muted, fontSize: 11)),
                            ],
                          ),
                          Column(
                            children: [
                              Text('${(_stats!['total_burned_aix'] as num?)?.toStringAsFixed(0) ?? 0}', style: const TextStyle(color: AixTheme.gold, fontSize: 24, fontWeight: FontWeight.w900)),
                              const Text('Сожжено AIX', style: TextStyle(color: AixTheme.muted, fontSize: 11)),
                            ],
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 20),
                  const Text('КАТАЛОГ', style: TextStyle(color: AixTheme.muted, fontSize: 11, letterSpacing: 2)),
                  const SizedBox(height: 10),
                  ..._catalog.map((c) => _catalogRow(c)),
                  const SizedBox(height: 20),
                  _card(
                    title: 'Мои артефакты (${_myArtifacts.length})',
                    children: _myArtifacts.isEmpty
                        ? [const Text('Пока пусто', style: TextStyle(color: AixTheme.muted, fontSize: 13))]
                        : _myArtifacts.map((a) => Text('${a['emoji']} ${a['name']}', style: const TextStyle(color: AixTheme.text, fontSize: 13))).toList(),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _catalogRow(Map<String, dynamic> c) {
    final level = c['name'] ?? '?';
    final emoji = c['emoji'] ?? '🔥';
    final price = c['price_aix'] ?? 0;
    final rarity = c['rarity'] ?? 'common';
    final levelKey = c['level'] ?? 'COMMON';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AixTheme.cosmos2,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AixTheme.red.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 28)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('$level ($rarity)', style: const TextStyle(color: AixTheme.text, fontSize: 14, fontWeight: FontWeight.w700)),
                Text('$price AIX', style: const TextStyle(color: AixTheme.muted, fontSize: 12)),
              ],
            ),
          ),
          ElevatedButton(
            onPressed: _busy ? null : () => _mint(levelKey),
            style: ElevatedButton.styleFrom(backgroundColor: AixTheme.red, foregroundColor: Colors.white),
            child: const Text('Сжечь', style: TextStyle(fontSize: 12)),
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

  Widget _localWarning() => Center(
        child: Padding(
          padding: const EdgeInsets.all(30),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.dns_outlined, color: AixTheme.amber, size: 60),
              const SizedBox(height: 16),
              const Text('Сжигание недоступно\nв автономном режиме', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
              const SizedBox(height: 12),
              const Text('Переключись на Внешнюю ноду', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.muted, fontSize: 13)),
            ],
          ),
        ),
      );
}
'''

# =============================================================================
# 5. SYNC SCREEN
# =============================================================================
sync_code = r'''/// AIX OS — Синхронизация.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../services/node_client.dart';
import '../theme.dart';

class SyncScreen extends StatefulWidget {
  const SyncScreen({super.key});
  @override
  State<SyncScreen> createState() => _SyncScreenState();
}

class _SyncScreenState extends State<SyncScreen> {
  bool _busy = false;
  String _result = '';

  Future<void> _pullChain() async {
    setState(() { _busy = true; _result = 'Синхронизация цепочки...'; });
    final active = context.read<ActiveNodeService>();
    if (active.isLocal) {
      setState(() { _busy = false; _result = 'Ошибка: Локальная нода'; });
      return;
    }
    final res = await active.remote._post('/sync/pull', {});
    if (!mounted) return;
    setState(() {
      _busy = false;
      _result = res != null && !res.containsKey('__error__') ? 'Цепочка синхронизирована!' : 'Ошибка: ${res?['__error__']}';
    });
  }

  Future<void> _pullState() async {
    setState(() { _busy = true; _result = 'Синхронизация протоколов...'; });
    final active = context.read<ActiveNodeService>();
    if (active.isLocal) {
      setState(() { _busy = false; _result = 'Ошибка: Локальная нода'; });
      return;
    }
    final res = await active.remote._post('/sync/state/pull', {});
    if (!mounted) return;
    setState(() {
      _busy = false;
      _result = res != null && !res.containsKey('__error__') ? 'Состояние протоколов синхронизировано!' : 'Ошибка: ${res?['__error__']}';
    });
  }

  @override
  Widget build(BuildContext context) {
    final active = context.watch<ActiveNodeService>();

    return Scaffold(
      backgroundColor: AixTheme.cosmos,
      appBar: AppBar(title: const Text('Синхронизация'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: active.isLocal
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(30),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.sync_problem, color: AixTheme.amber, size: 60),
                    const SizedBox(height: 16),
                    const Text('Выберите Внешнюю ноду\nдля синхронизации', textAlign: TextAlign.center, style: TextStyle(color: AixTheme.text, fontSize: 18, fontWeight: FontWeight.w800)),
                  ],
                ),
              ),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _card(
                    title: 'Принудительная синхронизация',
                    children: [
                      const Text('Если вы отстали от сети, нажмите одну из кнопок ниже.', style: TextStyle(color: AixTheme.muted, fontSize: 12)),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed: _busy ? null : _pullChain,
                        icon: const Icon(Icons.download),
                        label: const Text('Скачать цепочку (Chain)', style: TextStyle(fontWeight: FontWeight.w700)),
                        style: FilledButton.styleFrom(backgroundColor: AixTheme.purple, padding: const EdgeInsets.symmetric(vertical: 14)),
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton.icon(
                        onPressed: _busy ? null : _pullState,
                        icon: const Icon(Icons.sync_alt),
                        label: const Text('Скачать протоколы (State)', style: TextStyle(fontWeight: FontWeight.w700)),
                        style: OutlinedButton.styleFrom(foregroundColor: AixTheme.neon, side: const BorderSide(color: AixTheme.neon), padding: const EdgeInsets.symmetric(vertical: 14)),
                      ),
                    ],
                  ),
                  if (_result.isNotEmpty) ...[
                    const SizedBox(height: 20),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: AixTheme.cosmos2,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AixTheme.neon.withValues(alpha: 0.3)),
                      ),
                      child: Text(_result, style: const TextStyle(color: AixTheme.text, fontSize: 13, fontFamily: 'monospace')),
                    ),
                  ],
                ],
              ),
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
}
'''

# =============================================================================
# 6. BRAIN SCREEN
# =============================================================================
brain_code = r'''/// AIX OS — AIX Brain.
library;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/active_node_service.dart';
import '../theme.dart';

class BrainScreen extends StatefulWidget {
  const BrainScreen({super.key});
  @override
  State<BrainScreen> createState() => _BrainScreenState();
}

class _BrainScreenState extends State<BrainScreen> {
  final _msgCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final List<Map<String, String>> _messages = [];
  bool _busy = false;

  @override
  void dispose() {
    _msgCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _msgCtrl.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add({'role': 'user', 'text': text});
      _msgCtrl.clear();
      _busy = true;
    });
    _scrollToBottom();

    final active = context.read<ActiveNodeService>();
    if (active.isLocal) {
      setState(() {
        _messages.add({'role': 'brain', 'text': 'Brain недоступен в режиме локальной ноды. Переключитесь на Внешнюю ноду.'});
        _busy = false;
      });
      return;
    }

    final res = await active.remote.brainAsk(text);
    if (!mounted) return;

    String reply = 'Ошибка ответа';
    if (res != null && res['answer'] != null) {
      reply = res['answer'].toString();
    } else if (res != null && res.containsKey('__error__')) {
      reply = 'Ошибка: ${res['__error__']}';
    }

    setState(() {
      _messages.add({'role': 'brain', 'text': reply});
      _busy = false;
    });
    _scrollToBottom();
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
      appBar: AppBar(title: const Text('AIX Brain'), backgroundColor: AixTheme.cosmos2, foregroundColor: AixTheme.gold),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty
                ? const Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.psychology, size: 80, color: AixTheme.muted),
                        SizedBox(height: 16),
                        Text('Задайте любой вопрос', style: TextStyle(color: AixTheme.muted, fontSize: 16)),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollCtrl,
                    padding: const EdgeInsets.all(16),
                    itemCount: _messages.length,
                    itemBuilder: (_, i) {
                      final m = _messages[i];
                      final isUser = m['role'] == 'user';
                      return Align(
                        alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                        child: Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(14),
                          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
                          decoration: BoxDecoration(
                            color: isUser ? AixTheme.purple.withValues(alpha: 0.2) : AixTheme.cosmos2,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(color: isUser ? AixTheme.purple.withValues(alpha: 0.5) : AixTheme.neon.withValues(alpha: 0.3)),
                          ),
                          child: Text(m['text'] ?? '', style: const TextStyle(color: AixTheme.text, fontSize: 14, height: 1.4)),
                        ),
                      );
                    },
                  ),
          ),
          if (_busy) const LinearProgressIndicator(color: AixTheme.neon),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: const BoxDecoration(color: AixTheme.cosmos2),
            child: SafeArea(
              top: false,
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _msgCtrl,
                      style: const TextStyle(color: AixTheme.text),
                      decoration: InputDecoration(
                        hintText: 'Спросите что-нибудь...',
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
            ),
          ),
        ],
      ),
    );
  }
}
'''

# =============================================================================
# ЗАПИСЬ ФАЙЛОВ
# =============================================================================
(SCREENS / "lottery_screen.dart").write_text(lottery_code, encoding="utf-8")
print("✅ Создан lottery_screen.dart")

(SCREENS / "inherit_screen.dart").write_text(inherit_code, encoding="utf-8")
print("✅ Создан inherit_screen.dart")

(SCREENS / "aix_id_screen.dart").write_text(aixid_code, encoding="utf-8")
print("✅ Создан aix_id_screen.dart")

(SCREENS / "burn_screen.dart").write_text(burn_code, encoding="utf-8")
print("✅ Создан burn_screen.dart")

(SCREENS / "sync_screen.dart").write_text(sync_code, encoding="utf-8")
print("✅ Создан sync_screen.dart")

(SCREENS / "brain_screen.dart").write_text(brain_code, encoding="utf-8")
print("✅ Создан brain_screen.dart")

# =============================================================================
# ПАТЧ MAIN.DART
# =============================================================================
main_dart = FLUTTER / "main.dart"
content = main_dart.read_text(encoding="utf-8")

# 1. Добавляем импорты
if "lottery_screen.dart" not in content:
    content = content.replace(
        "import 'screens/timelock_screen.dart';",
        "import 'screens/timelock_screen.dart';\nimport 'screens/lottery_screen.dart';\nimport 'screens/inherit_screen.dart';\nimport 'screens/aix_id_screen.dart';\nimport 'screens/burn_screen.dart';\nimport 'screens/sync_screen.dart';\nimport 'screens/brain_screen.dart';"
    )

# 2. Заменяем маршруты
content = content.replace(
    "          '/inherit': (context) => const PlaceholderScreen(\n                title: 'Наследство',\n                emoji: '🎗',\n                description: 'DMS. Скоро в батче 5.',\n              ),",
    "          '/inherit': (context) => const InheritScreen(),"
)
content = content.replace(
    "          '/brain': (context) => const PlaceholderScreen(\n                title: 'AIX Brain',\n                emoji: '🧠',\n                description: 'AI-напарник. Скоро в батче 5.',\n              ),",
    "          '/brain': (context) => const BrainScreen(),"
)

# Добавляем новые маршруты, которых не было в main.dart
if "'/lottery'" not in content:
    content = content.replace(
        "          '/inherit': (context) => const InheritScreen(),",
        "          '/inherit': (context) => const InheritScreen(),\n          '/lottery': (context) => const LotteryScreen(),\n          '/aixid': (context) => const AixIdScreen(),\n          '/burn': (context) => const BurnScreen(),\n          '/sync': (context) => const SyncScreen(),"
    )

main_dart.write_text(content, encoding="utf-8")
print("✅ Обновлён main.dart (маршруты Lottery, Inherit, AIX-ID, Burn, Sync, Brain)")

# =============================================================================
# ПАТЧ PROTOCOLS_TAB.DART
# =============================================================================
proto_dart = FLUTTER / "screens" / "protocols_tab.dart"
content = proto_dart.read_text(encoding="utf-8")

content = content.replace("_P('🎰', 'Lottery', 'Розыгрыш', null)", "_P('🎰', 'Lottery', 'Розыгрыш', '/lottery')")
content = content.replace("_P('🎗', 'DMS', 'Наследство', '/inherit')", "_P('🎗', 'DMS', 'Наследство', '/inherit')")
content = content.replace("_P('🪪', 'AIX-ID', '@имя', null)", "_P('🪪', 'AIX-ID', '@имя', '/aixid')")
content = content.replace("_P('🔥', 'Burn', 'Сжигание', null)", "_P('🔥', 'Burn', 'Сжигание', '/burn')")
content = content.replace("_P('🔄', 'Sync', 'Синхронизация', null)", "_P('🔄', 'Sync', 'Синхронизация', '/sync')")
content = content.replace("_P('🧠', 'Brain', 'AI-напарник', '/brain')", "_P('🧠', 'Brain', 'AI-напарник', '/brain')")

proto_dart.write_text(content, encoding="utf-8")
print("✅ Обновлён protocols_tab.dart")

print("\n🎉 Батч 5 готов! Нажми R в терминале Flutter.")