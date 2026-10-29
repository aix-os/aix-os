import 'package:aix_os/services/wallet_service.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    // Пустое in-memory хранилище для каждого теста
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('WalletService создаёт кошелёк', () async {
    final svc = WalletService();
    final w = await svc.createWallet(name: 'test-wallet');

    expect(w.address.startsWith('AIX'), true);
    expect(w.privateKeyHex.length, 64);
    expect(w.publicKey.length, 66);
    expect(w.name, 'test-wallet');
  });

  test('WalletService сохраняет и читает адрес', () async {
    final svc = WalletService();
    await svc.createWallet(name: 'persist-test');

    expect(await svc.hasWallet(), true);
    final addr = await svc.getWalletAddress();
    expect(addr, isNotNull);
    expect(addr!.startsWith('AIX'), true);
  });

  test('WalletService удаляется корректно', () async {
    final svc = WalletService();
    await svc.createWallet(name: 'to-delete');
    expect(await svc.hasWallet(), true);

    await svc.deleteWallet('dummy');
    expect(await svc.hasWallet(), false);
  });

  test('WalletService импорт из hex даёт тот же адрес (эталон Python)', () async {
    final svc = WalletService();
    const privHex = '0000000000000000000000000000000000000000000000000000000000000001';
    final w = await svc.importFromHex(privHex);

    expect(w.address, 'AIXTLeUZDGLWnyiJVFcp3m3M1782uBsGWa8uf');
  });

  test('PIN: установка и проверка', () async {
    final svc = WalletService();
    await svc.createWallet(name: 'pin-test');
    await svc.setPin('1234');

    expect(await svc.hasPin(), true);
    expect(await svc.checkPin('1234'), true);
    expect(await svc.checkPin('9999'), false);
  });
}