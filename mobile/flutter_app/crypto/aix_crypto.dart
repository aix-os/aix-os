/// AIX OS — криптография на устройстве.
///
/// Всё, что нужно для кошелька:
/// - SHA256, RIPEMD160, hash160
/// - Base58, Base58Check
/// - ECDSA secp256k1: приватный ключ, публичный (compressed), подпись (DER)
/// - Адреса AIX: "AIX" + Base58Check(0x41 + hash160(pubkey))
///
/// Формат совпадает с crypto/keys.py и crypto/address.py в Python-части.
library;

import 'dart:typed_data';

import 'package:crypto/crypto.dart' as crypto;
import 'package:pointycastle/export.dart';

// =========================================================================
// КОНСТАНТЫ
// =========================================================================

/// Версия AIX-адреса. 0x41 = 65 = "A" (как намёк на AIX).
const int AIX_VERSION_BYTE = 0x41;

/// Префикс адреса.
const String AIX_PREFIX = 'AIX';

/// Base58-алфавит (без 0, O, I, l — чтобы не путать).
const String _b58Alphabet =
    '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

/// Кривая secp256k1 (та же, что Bitcoin/Ethereum).
final ECDomainParameters _secp256k1 = ECCurve_secp256k1();

// =========================================================================
// ХЕШИ
// =========================================================================

/// SHA256 от байтов.
Uint8List sha256(Uint8List data) {
  return Uint8List.fromList(crypto.sha256.convert(data).bytes);
}

/// Двойной SHA256 (используется в checksum-ах Bitcoin-подобных адресов).
Uint8List doubleSha256(Uint8List data) {
  return sha256(sha256(data));
}

/// RIPEMD160 от байтов. Возвращает 20 байт.
Uint8List ripemd160(Uint8List data) {
  final digest = RIPEMD160Digest();
  digest.update(data, 0, data.length);
  final out = Uint8List(digest.digestSize);
  digest.doFinal(out, 0);
  return out;
}

/// hash160 = RIPEMD160(SHA256(data)). Классика для криптоадресов.
Uint8List hash160(Uint8List data) {
  return ripemd160(sha256(data));
}

// =========================================================================
// BASE58 / BASE58CHECK
// =========================================================================

/// Base58-кодирование (Bitcoin-алфавит).
String base58Encode(Uint8List data) {
  // Считаем ведущие нули: каждый становится '1'.
  int zeros = 0;
  while (zeros < data.length && data[zeros] == 0) {
    zeros++;
  }

  // Переводим в BigInt.
  BigInt num = BigInt.zero;
  for (final b in data) {
    num = num * BigInt.from(256) + BigInt.from(b);
  }

  final sb = StringBuffer();
  final fiftyEight = BigInt.from(58);
  while (num > BigInt.zero) {
    final r = (num % fiftyEight).toInt();
    sb.write(_b58Alphabet[r]);
    num = num ~/ fiftyEight;
  }

  // Реверс + ведущие '1' вместо нулей.
  final encoded = sb.toString().split('').reversed.join();
  return '1' * zeros + encoded;
}

/// Base58-декодирование.
Uint8List base58Decode(String s) {
  BigInt num = BigInt.zero;
  for (int i = 0; i < s.length; i++) {
    final idx = _b58Alphabet.indexOf(s[i]);
    if (idx < 0) {
      throw FormatException('Invalid base58 char: ${s[i]}');
    }
    num = num * BigInt.from(58) + BigInt.from(idx);
  }

  int zeros = 0;
  while (zeros < s.length && s[zeros] == '1') {
    zeros++;
  }

  final bytes = <int>[];
  final twoFiftySix = BigInt.from(256);
  while (num > BigInt.zero) {
    bytes.add((num % twoFiftySix).toInt());
    num = num ~/ twoFiftySix;
  }
  bytes.addAll(List.filled(zeros, 0));
  return Uint8List.fromList(bytes.reversed.toList());
}

/// Base58Check: base58(payload + checksum[:4]).
String base58CheckEncode(Uint8List payload) {
  final checksum = doubleSha256(payload).sublist(0, 4);
  final combined = Uint8List(payload.length + 4)
    ..setRange(0, payload.length, payload)
    ..setRange(payload.length, payload.length + 4, checksum);
  return base58Encode(combined);
}

/// Base58Check-декодирование. Возвращает payload без checksum или null.
Uint8List? base58CheckDecode(String encoded) {
  try {
    final decoded = base58Decode(encoded);
    if (decoded.length < 5) return null;
    final payload = decoded.sublist(0, decoded.length - 4);
    final checksum = decoded.sublist(decoded.length - 4);
    final expected = doubleSha256(payload).sublist(0, 4);
    for (int i = 0; i < 4; i++) {
      if (checksum[i] != expected[i]) return null;
    }
    return payload;
  } catch (_) {
    return null;
  }
}

// =========================================================================
// ECDSA SECP256K1
// =========================================================================

/// 32-байтовый BigInt -> Uint8List.
Uint8List _bigIntTo32Bytes(BigInt n) {
  final out = Uint8List(32);
  final byteMask = BigInt.from(0xff);
  for (int i = 31; i >= 0; i--) {
    out[i] = (n & byteMask).toInt();
    n = n >> 8;
  }
  return out;
}

/// Uint8List -> BigInt.
BigInt _bytesToBigInt(Uint8List bytes) {
  BigInt n = BigInt.zero;
  for (final b in bytes) {
    n = (n << 8) | BigInt.from(b);
  }
  return n;
}

/// Приватный ключ из 32 байт.
ECPrivateKey privateKeyFromBytes(Uint8List bytes) {
  if (bytes.length != 32) {
    throw ArgumentError('Private key must be 32 bytes, got ${bytes.length}');
  }
  final d = _bytesToBigInt(bytes);
  final n = _secp256k1.n;
  if (d <= BigInt.zero || (n != null && d >= n)) {
    throw ArgumentError('Private key out of range');
  }
  return ECPrivateKey(d, _secp256k1);
}

/// Приватный ключ → 32-байтовое представление.
Uint8List privateKeyToBytes(ECPrivateKey privKey) {
  return _bigIntTo32Bytes(privKey.d!);
}

/// Публичный ключ в сжатом виде (33 байта, начинается с 0x02 или 0x03).
Uint8List getCompressedPublicKey(ECPrivateKey privKey) {
  final q = privKey.parameters!.G * privKey.d!;
  return q!.getEncoded(true);
}

/// Публичный ключ (compressed, 33 байта) → адрес AIX.
String publicKeyToAddress(Uint8List compressedPubKey) {
  final h = hash160(compressedPubKey);
  final payload = Uint8List(1 + h.length)
    ..[0] = AIX_VERSION_BYTE
    ..setRange(1, 1 + h.length, h);
  final encoded = base58CheckEncode(payload);
  return '$AIX_PREFIX$encoded';
}

/// Приватный ключ → адрес AIX.
String privateKeyToAddress(ECPrivateKey privKey) {
  final pub = getCompressedPublicKey(privKey);
  return publicKeyToAddress(pub);
}

/// AIX-адрес → hash160 (20 байт). null — если невалидный.
Uint8List? addressToHash160(String address) {
  if (!address.startsWith(AIX_PREFIX)) return null;
  final encoded = address.substring(AIX_PREFIX.length);
  final payload = base58CheckDecode(encoded);
  if (payload == null || payload.length != 21) return null;
  if (payload[0] != AIX_VERSION_BYTE) return null;
  return payload.sublist(1);
}

/// Валидация AIX-адреса.
bool isValidAixAddress(String address) {
  return addressToHash160(address) != null;
}

// =========================================================================
// ПОДПИСЬ
// =========================================================================

/// Подписать сообщение приватным ключом.
///
/// Формат: SHA256(message) -> ECDSA -> DER-кодированная подпись.
/// Точное соответствие Python-части проверим отдельным тестом.
Uint8List signMessage(ECPrivateKey privKey, Uint8List message) {
  final signer = ECDSASigner(null, null)
    ..init(true, PrivateKeyParameter<ECPrivateKey>(privKey));
  final hash = sha256(message);
  final sig = signer.generateSignature(hash) as ECSignature;
  return _encodeDerSignature(sig);
}

/// DER-кодирование ECDSA-подписи (SEQUENCE из двух INTEGER).
Uint8List _encodeDerSignature(ECSignature sig) {
  final rBytes = _minimalSignedBytes(sig.r);
  final sBytes = _minimalSignedBytes(sig.s);
  final totalLen = 2 + rBytes.length + 2 + sBytes.length;
  final out = BytesBuilder();
  out.addByte(0x30); // SEQUENCE
  out.addByte(totalLen);
  out.addByte(0x02); // INTEGER r
  out.addByte(rBytes.length);
  out.add(rBytes);
  out.addByte(0x02); // INTEGER s
  out.addByte(sBytes.length);
  out.add(sBytes);
  return out.toBytes();
}

/// BigInt -> минимальный BE-байтовый массив (с ведущим 0x00 если старший бит 1).
Uint8List _minimalSignedBytes(BigInt n) {
  if (n == BigInt.zero) return Uint8List.fromList([0]);
  final raw = <int>[];
  final byteMask = BigInt.from(0xff);
  BigInt tmp = n;
  while (tmp > BigInt.zero) {
    raw.add((tmp & byteMask).toInt());
    tmp = tmp >> 8;
  }
  final bytes = raw.reversed.toList();
  // Если старший бит установлен — нужен ведущий 0x00.
  if (bytes.isNotEmpty && (bytes[0] & 0x80) != 0) {
    bytes.insert(0, 0);
  }
  return Uint8List.fromList(bytes);
}