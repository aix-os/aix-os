import 'dart:typed_data';

import 'package:aix_os/crypto/aix_crypto.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Address derivation', () {
    test('private key 0x...0001 -> expected AIX address (matches Python)', () {
      // Эталон из Python:
      //   PRIV: 0000000000000000000000000000000000000000000000000000000000000001
      //   ADDR: AIXTLeUZDGLWnyiJVFcp3m3M1782uBsGWa8uf
      final privBytes = Uint8List(32);
      privBytes[31] = 1;

      final privKey = privateKeyFromBytes(privBytes);
      final pubKey = getCompressedPublicKey(privKey);
      final address = publicKeyToAddress(pubKey);

      expect(address, 'AIXTLeUZDGLWnyiJVFcp3m3M1782uBsGWa8uf');
    });

    test('private key 0x...002a -> valid AIX address', () {
      final privBytes = Uint8List(32);
      privBytes[31] = 42;
      final privKey = privateKeyFromBytes(privBytes);
      final address = privateKeyToAddress(privKey);

      expect(address.startsWith('AIX'), true);
      expect(isValidAixAddress(address), true);
    });

    test('isValidAixAddress rejects broken addresses', () {
      expect(isValidAixAddress('AIX0000000000000000000000000000000000'), false);
      expect(isValidAixAddress('not-an-aix-address'), false);
      expect(isValidAixAddress(''), false);
    });
  });

  group('Base58Check', () {
    test('roundtrip: encode -> decode = same bytes', () {
      final data = Uint8List.fromList([0x41, 1, 2, 3, 4, 5]);
      final encoded = base58CheckEncode(data);
      final decoded = base58CheckDecode(encoded);
      expect(decoded, isNotNull);
      expect(decoded!.length, data.length);
      for (int i = 0; i < data.length; i++) {
        expect(decoded[i], data[i]);
      }
    });

    test('checksum rejects corrupted data', () {
      final data = Uint8List.fromList([0x41, 1, 2, 3, 4, 5]);
      final encoded = base58CheckEncode(data);
      // Меняем один символ в середине на другой из алфавита
      final mid = encoded.length ~/ 2;
      final corrupted = encoded.substring(0, mid) +
          'Z' +
          encoded.substring(mid + 1);
      expect(base58CheckDecode(corrupted), isNull);
    });
  });

  group('Hashes', () {
    test('hash160 of empty bytes is 20 bytes', () {
      final h = hash160(Uint8List(0));
      expect(h.length, 20);
    });

    test('doubleSha256 of empty bytes is 32 bytes', () {
      final h = doubleSha256(Uint8List(0));
      expect(h.length, 32);
    });
  });
}