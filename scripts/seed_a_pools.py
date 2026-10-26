import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Импортируем обновленный менеджер
from core.protocols.swap import SwapManager, COIN_CATALOG

PORT = 8010
STORAGE = Path(f"data/swap_{PORT}.json")
CREATOR = "AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2" # Твой кошелек (Alice)

mgr = SwapManager(STORAGE)

# Выдаем тебе нативный AIX для создания пулов (виртуальный баланс для свапа)
TEST_AIX = 100_000_000 * 10**18  # 100 млн AIX
mgr.add_balance(CREATOR, "AIX", TEST_AIX)
print(f"💰 Выдано {TEST_AIX/10**18:.0f} AIX для создания пулов")

# Создаем пулы с курсами от $100 за AIX
for token, info in COIN_CATALOG.items():
    if token == "AIX":
        continue # AIX не создаем в паре с самим собой
        
    usd = info["usd_price"]
    # Цена AIX = $100. Значит 1 COIN = (usd / 100) AIX.
    aix_amount = usd / 100.0 
    
    # Создаем пул: 1000 COIN и соответствующее количество AIX
    a_coin_amount = 1000 * 10**18
    aix_pool_amount = int(1000 * aix_amount * 10**18)
    
    # Выдаем тебе 1000 COIN для теста
    mgr.add_balance(CREATOR, token, a_coin_amount)
    
    ok, msg, pool = mgr.create_pool(
        token_x="AIX", 
        token_y=token, 
        amount_x=aix_pool_amount, 
        amount_y=a_coin_amount, 
        creator=CREATOR
    )
    if ok:
        print(f"✅ Пул {token}/AIX. Курс: 1 {token} = {aix_amount:.4f} AIX (= ${usd})")
    else:
        print(f"❌ Ошибка пула {token}: {msg}")

mgr._save()
print("\n💎 Империя создана! Запускай ноду и заходи в Swap.")
