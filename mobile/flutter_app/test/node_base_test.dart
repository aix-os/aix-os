import 'package:aix_os/node/config_node.dart';
import 'package:aix_os/node/models/block.dart';
import 'package:aix_os/node/models/chain.dart';
import 'package:aix_os/node/models/transaction.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Local Node — базовые тесты', () {
    test('Genesis создаётся, hash и merkle не пустые', () {
      final g = Block.createGenesis(message: 'AIX OS — Genesis Block');
      expect(g.index, 0);
      expect(g.previousHash, '0' * 64);
      expect(g.hash.length, 64);
      expect(g.merkleRoot.length, 64);
    });

    test('Chain создаёт genesis автоматически', () {
      final c = Chain();
      expect(c.chain.length, 1);
      expect(c.height(), 0);
      expect(c.difficulty, greaterThanOrEqualTo(1));
    });

    test('Mine находит блок со сложностью 2', () {
      final block = Block(
        index: 1,
        timestamp: 1735689700.0,
        transactions: [],
        previousHash: '0' * 64,
      );
      final attempts = block.mine(2);
      expect(block.hash.startsWith('00'), true);
      expect(attempts, greaterThan(0));
    });

    test('Проверка блока: рабочий блок валиден', () {
      final genesis = Block.createGenesis(message: 'AIX OS — Genesis Block');
      final block1 = Block(
        index: 1,
        timestamp: 1735689700.0,
        transactions: [],
        previousHash: genesis.hash,
      );
      block1.mine(2);
      final (ok, msg) = block1.isValid(
        previousBlock: genesis,
        difficulty: 2,
      );
      expect(ok, true, reason: 'msg=$msg');
    });

    test('Transaction COINBASE валиден (50 AIX при SATOSHI=10^8)', () {
      // 50 AIX = 50 * 10^8 = 5 × 10^9 — влезает в int64
      final tx = Transaction(
        sender: 'COINBASE',
        recipient: 'AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2',
        amount: 50 * SATOSHI,
        timestamp: 1735689600.0,
        message: 'AIX OS — майнинг награда',
      );
      final (ok, msg) = tx.validate();
      expect(ok, true, reason: 'msg=$msg');
    });

    test('Genesis hash для сверки с Python', () {
      final g = Block.createGenesis(message: 'AIX OS — Genesis Block');
      // ignore: avoid_print
      print('DART_MERKLE: ${g.merkleRoot}');
      // ignore: avoid_print
      print('DART_HASH:   ${g.hash}');
      expect(g.hash.length, 64);
    });
  });
}