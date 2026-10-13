import 'dart:convert';
import 'dart:io';

import 'package:aix_os/services/tx_signer.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('Dart подписывает транзакцию и пишет в файл для проверки Python', () async {
    // Приватный ключ 0x...0001 → адрес AIXTLeUZDGLWnyiJVFcp3m3M1782uBsGWa8uf
    const privHex =
        '0000000000000000000000000000000000000000000000000000000000000001';
    const sender = 'AIXTLeUZDGLWnyiJVFcp3m3M1782uBsGWa8uf';
    const recipient = 'AIXTDTWaRqhPzdfmGSgp66G1vg9Rtma1k5WKC';

    final tx = signTransaction(
      privateKeyHex: privHex,
      sender: sender,
      recipient: recipient,
      amount: 100000000, // 1 AIX в сатоши (8 знаков)
      fee: 0,
      message: 'E2E cross-language test',
      timestampOverride: 1791833002, // фиксируем для воспроизводимости
    );

    // Пишем файл — Python его прочитает.
    final outDir = Directory('e2e_out');
    if (!outDir.existsSync()) outDir.createSync(recursive: true);
    final outFile = File('${outDir.path}/signed_tx.json');
    await outFile.writeAsString(
      const JsonEncoder.withIndent('  ').convert(tx.toJson()),
    );

    // Проверки на стороне Dart.
    expect(tx.sender, sender);
    expect(tx.txId.length, 64);
    expect(await outFile.exists(), true);

    // eslint-disable-next-line avoid_print
    print('WROTE: ${outFile.absolute.path}');
  });
}