"""Патч для внедрения реальных курсов CoinGecko."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
FLUTTER = ROOT / "mobile" / "flutter_app" / "lib"

# 1. Создаём currency_service.dart
service_code = '''/// AIX OS — получение реальных курсов с CoinGecko.
library;

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class CurrencyService extends ChangeNotifier {
  Map<String, double> _prices = {
    'BTC': 65000.0,
    'ETH': 3500.0,
    'USDT': 1.0,
    'BNB': 600.0,
    'SOL': 150.0,
    'TON': 7.5,
    'XRP': 0.5,
    'DOGE': 0.15,
  };

  Map<String, double> get prices => _prices;

  Future<void> fetchPrices() async {
    try {
      final url = Uri.parse('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether,binancecoin,solana,the-open-network,ripple,dogecoin&vs_currencies=usd');
      final res = await http.get(url).timeout(const Duration(seconds: 10));
      
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        _prices['BTC'] = (data['bitcoin']?['usd'] as num?)?.toDouble() ?? _prices['BTC']!;
        _prices['ETH'] = (data['ethereum']?['usd'] as num?)?.toDouble() ?? _prices['ETH']!;
        _prices['USDT'] = (data['tether']?['usd'] as num?)?.toDouble() ?? _prices['USDT']!;
        _prices['BNB'] = (data['binancecoin']?['usd'] as num?)?.toDouble() ?? _prices['BNB']!;
        _prices['SOL'] = (data['solana']?['usd'] as num?)?.toDouble() ?? _prices['SOL']!;
        _prices['TON'] = (data['the-open-network']?['usd'] as num?)?.toDouble() ?? _prices['TON']!;
        _prices['XRP'] = (data['ripple']?['usd'] as num?)?.toDouble() ?? _prices['XRP']!;
        _prices['DOGE'] = (data['dogecoin']?['usd'] as num?)?.toDouble() ?? _prices['DOGE']!;
        
        notifyListeners();
        debugPrint('✅ CoinGecko: курсы обновлены');
      }
    } catch (e) {
      debugPrint('❌ CoinGecko error: $e');
    }
  }
}
'''
(FLUTTER / "services" / "currency_service.dart").write_text(service_code, encoding="utf-8")
print("✅ Создан currency_service.dart")

# 2. Обновляем main.dart (добавляем импорт и провайдер)
main_dart = FLUTTER / "main.dart"
content = main_dart.read_text(encoding="utf-8")
if "currency_service.dart" not in content:
    content = content.replace(
        "import 'services/wallet_service.dart';",
        "import 'services/wallet_service.dart';\nimport 'services/currency_service.dart';"
    )
    content = content.replace(
        "ChangeNotifierProvider(create: (_) => WalletService()),",
        "ChangeNotifierProvider(create: (_) => WalletService()),\n        ChangeNotifierProvider(create: (_) => CurrencyService()..fetchPrices()),"
    )
    main_dart.write_text(content, encoding="utf-8")
    print("✅ Обновлён main.dart")

# 3. Обновляем home_screen.dart (убираем привязку к remote)
home_dart = FLUTTER / "screens" / "home_screen.dart"
content = home_dart.read_text(encoding="utf-8")
if "CurrencyTicker(client: active.remote)" in content:
    content = content.replace(
        "CurrencyTicker(client: active.remote)",
        "const CurrencyTicker()"
    )
    home_dart.write_text(content, encoding="utf-8")
    print("✅ Обновлён home_screen.dart")

# 4. Обновляем currency_ticker.dart (теперь он берёт данные из провайдера)
ticker_code = '''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/currency_service.dart';
import '../theme.dart';

class CurrencyTicker extends StatelessWidget {
  const CurrencyTicker({super.key});

  @override
  Widget build(BuildContext context) {
    final svc = context.watch<CurrencyService>();
    final prices = svc.prices;
    
    final list = [
      _CoinPrice('AIX', '⚡', 100.00, 0.00, AixTheme.gold),
      _CoinPrice('USDT', '💵', prices['USDT'] ?? 1.0, 0.00, AixTheme.green),
      _CoinPrice('BTC', '🟠', prices['BTC'] ?? 65000.0, 0.00, const Color(0xFFF7931A)),
      _CoinPrice('ETH', '💎', prices['ETH'] ?? 3500.0, 0.00, const Color(0xFF627EEA)),
      _CoinPrice('BNB', '🟡', prices['BNB'] ?? 600.0, 0.00, const Color(0xFFF0B90B)),
      _CoinPrice('SOL', '🟣', prices['SOL'] ?? 150.0, 0.00, const Color(0xFF9945FF)),
      _CoinPrice('TON', '🔵', prices['TON'] ?? 7.5, 0.00, const Color(0xFF0098EA)),
      _CoinPrice('XRP', '💧', prices['XRP'] ?? 0.5, 0.00, const Color(0xFF23292F)),
      _CoinPrice('DOGE', '🐕', prices['DOGE'] ?? 0.15, 0.00, const Color(0xFFC2A633)),
    ];

    return SizedBox(
      height: 118,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        itemCount: list.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) => _coinChip(list[i]),
      ),
    );
  }

  Widget _coinChip(_CoinPrice c) {
    return Container(
      width: 130,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: AixTheme.cosmos2,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.color.withValues(alpha: 0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Text(c.emoji, style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 6),
              Text(
                c.symbol,
                style: TextStyle(
                  color: c.color,
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _fmtPrice(c.priceUsd),
                style: const TextStyle(
                  color: AixTheme.text,
                  fontSize: 16,
                  fontWeight: FontWeight.w800,
                  fontFamily: 'monospace',
                ),
              ),
              const SizedBox(height: 2),
              Row(
                children: [
                  Icon(
                    c.change24 >= 0 ? Icons.trending_up_rounded : Icons.trending_down_rounded,
                    size: 12,
                    color: c.change24 >= 0 ? AixTheme.green : AixTheme.red,
                  ),
                  const SizedBox(width: 3),
                  Text(
                    '\${c.change24 >= 0 ? '+' : ''}\${c.change24.toStringAsFixed(2)}%',
                    style: TextStyle(
                      color: c.change24 >= 0 ? AixTheme.green : AixTheme.red,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  static String _fmtPrice(double usd) {
    if (usd >= 10000) return '\\\$\${usd.toStringAsFixed(0)}';
    if (usd >= 1000) return '\\\$\${usd.toStringAsFixed(1)}';
    if (usd >= 1) return '\\\$\${usd.toStringAsFixed(2)}';
    if (usd >= 0.01) return '\\\$\${usd.toStringAsFixed(4)}';
    return '\\\$\${usd.toStringAsFixed(6)}';
  }
}

class _CoinPrice {
  final String symbol;
  final String emoji;
  final double priceUsd;
  final double change24;
  final Color color;

  const _CoinPrice(this.symbol, this.emoji, this.priceUsd, this.change24, this.color);
}
'''
(FLUTTER / "widgets" / "currency_ticker.dart").write_text(ticker_code, encoding="utf-8")
print("✅ Обновлён currency_ticker.dart")

print("\n🎉 Готово! Нажми R в терминале Flutter.")