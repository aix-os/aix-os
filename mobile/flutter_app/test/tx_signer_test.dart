import 'package:aix_os/services/tx_signer.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('canonical payload совпадает с Python-форматом', () {
    final payload = buildSigningPayload(
      sender: 'AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2',
      recipient: 'AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC',
      amount: 100000000, // 1 AIX в сатоши
      timestamp: 1791833002,
      fee: 0,
      message: '',
    );
    final s = String.fromCharCodes(payload);
    // Ключи в алфавитном порядке: amount, fee, message, recipient, sender, timestamp
    expect(
      s,
      '{"amount":100000000,"fee":0,"message":"","recipient":"AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC","sender":"AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2","timestamp":1791833002}',
    );
  });

  test('message с unicode экранируется как Python', () {
    final s = jsonString('привет');
    // Python json.dumps("привет", ensure_ascii=True) = "\u043f\u0440\u0438\u0432\u0435\u0442"
    expect(s, '"\\u043f\\u0440\\u0438\\u0432\\u0435\\u0442"');
  });

  test('message с кавычками экранируется', () {
    expect(jsonString('a"b'), '"a\\"b"');
    expect(jsonString('a\\b'), '"a\\\\b"');
    expect(jsonString('a\nb'), '"a\\nb"');
  });

  test('подпись транзакции работает и даёт валидный hex', () {
    const privHex =
        '0000000000000000000000000000000000000000000000000000000000000001';
    final sender = 'AIXTLeUZDGLWnyiJVFcp3m3M1782uBsGWa8uf';

    final tx = signTransaction(
      privateKeyHex: privHex,
      sender: sender,
      recipient: 'AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC',
      amount: 100000000,
      fee: 0,
      message: '',
      timestampOverride: 1791833002,
    );

    expect(tx.publicKeyHex.length, 66); // 33 байта hex
    expect(tx.signatureHex.length > 130, true); // DER ~70-72 байт hex
    expect(tx.txId.length, 64); // sha256 hex
    expect(tx.sender, sender);
  });
}