"""AIX OS — Командная строка (Gift + TimeLock + SBT + Lottery + DMS + AIX-ID + Burn + Contacts + Swap + PoC)."""
import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from colorama import Fore, init as colorama_init
from tabulate import tabulate
import config
from core.chain import Blockchain
from core.wallet import Wallet
from core.block import Block
from core.transaction import Transaction
from storage.db import ChainStorage
from crypto.address import is_valid_address
from core.protocols.ai_memory import (
    AIMemoryManager, KINDS as AI_KINDS, PRIORITIES as AI_PRIORITIES,
    KIND_EMOJI, PRIORITY_EMOJI,
)
from core.governance.dao import DAOManager
from core.protocols.faucet import FaucetManager

colorama_init(autoreset=True)
storage = ChainStorage(config.CHAIN_DB_PATH)

DEFAULT_NODE = "http://localhost:8010"


def load_chain():
    chain = storage.load()
    if chain is None:
        chain = Blockchain()
        storage.save(chain)
    return chain


def _node_url(a):
    return getattr(a, "node", None) or DEFAULT_NODE


def _node_get(url: str, endpoint: str, timeout: float = 10.0):
    try:
        r = requests.get(f"{url}{endpoint}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


def resolve(who, node_url=None):
    if not who:
        raise ValueError("Пустой параметр")
    if Wallet.exists(who):
        w = Wallet.load(who)
        return w.address, f"{who} ({w.address[:20]}...)"
    if is_valid_address(who):
        return who, who
    name = who.lstrip("@")
    if node_url is None:
        node_url = DEFAULT_NODE
    data = _node_get(node_url, f"/id/resolve/{name}")
    if data and data.get("address"):
        return data["address"], f"@{name} ({data['address'][:20]}...)"
    raise ValueError(f"'{who}' — не кошелёк, не AIX-ID и не AIX-адрес")


# =============================================================================
# WALLET / BALANCE / MINE / SEND / CHAIN / QR
# =============================================================================

def cmd_wallet_new(a):
    if Wallet.exists(a.name):
        print(f"{Fore.RED}❌ '{a.name}' уже существует"); return 1
    w = Wallet.create(a.name); path = w.save()
    print(f"{Fore.GREEN}✅ Кошелёк '{a.name}' создан")
    print(f"   {Fore.CYAN}Адрес: {Fore.YELLOW}{w.address}")
    print(f"   {Fore.CYAN}Файл:  {path}")
    print(f"   {Fore.RED}⚠️  Приватный ключ в файле. Никому не показывай!")
    print(f"\n   {Fore.CYAN}Зарегистрируй AIX-ID: aix id register {a.name} <имя>")
    return 0


def cmd_wallet_list(a):
    names = Wallet.list_wallets()
    if not names:
        print(f"{Fore.YELLOW}Нет кошельков."); return 0
    url = _node_url(a)
    node_wallets = _node_get(url, "/wallets")
    node_data = {w["name"]: w for w in node_wallets["wallets"]} if node_wallets else None

    rows = []
    for name in names:
        try:
            w = Wallet.load(name)
            if node_data and name in node_data and "error" not in node_data[name]:
                d = node_data[name]
                rep = d.get("reputation", 0)
                medals = d.get("medals", 0)
                rep_str = f"{rep}🏅{medals}" if medals else "—"
                aix_id = d.get("aix_id")
                avatar = d.get("avatar") or ""
                id_str = f"{avatar}@{aix_id}" if aix_id else "—"
                contacts = d.get("contacts", 0)
                contacts_str = f"📇{contacts}" if contacts else "—"
                rows.append([name, id_str, w.address,
                             f"{d['balance_aix']:.4f}",
                             f"{d.get('locked_aix', 0):.4f}",
                             f"{d.get('available_aix', d['balance_aix']):.4f}",
                             rep_str, contacts_str])
            else:
                chain = load_chain()
                bal = chain.get_balance(w.address) / config.SATOSHI
                rows.append([name, "—", w.address, f"{bal:.4f}", "?", "?", "?", "?"])
        except Exception as e:
            rows.append([name, "ERROR", str(e), "", "", "", "", ""])

    source = f"нода {url}" if node_data else "локальный chain.json"
    print(f"{Fore.CYAN}👛 Кошельки AIX (источник: {source}):")
    print(tabulate(rows, headers=["Имя", "AIX-ID", "Адрес", "Баланс", "Заморожено", "Доступно", "Репутация", "Контакты"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_wallet_show(a):
    try: w = Wallet.load(a.name)
    except FileNotFoundError:
        print(f"{Fore.RED}❌ Кошелёк '{a.name}' не найден"); return 1
    url = _node_url(a)
    node_bal = _node_get(url, f"/balance/{w.address}")
    if node_bal:
        bal = node_bal["balance_aix"]
        locked = node_bal.get("locked_aix", 0)
        avail = node_bal.get("available_aix", bal)
        rep = node_bal.get("reputation", 0)
        medals = node_bal.get("medals_count", 0)
        aix_id = node_bal.get("name")
    else:
        chain = load_chain()
        bal = chain.get_balance(w.address) / config.SATOSHI
        locked, avail = 0, bal
        rep, medals, aix_id = 0, 0, None

    print(f"{Fore.CYAN}👛 Кошелёк: {Fore.YELLOW}{w.name}")
    if aix_id: print(f"   AIX-ID:     {Fore.YELLOW}@{aix_id}")
    print(f"   Адрес:      {Fore.YELLOW}{w.address}")
    print(f"   Баланс:     {Fore.YELLOW}{bal:.4f} AIX")
    if locked:
        print(f"   Заморожено: {Fore.YELLOW}{locked:.4f} AIX")
        print(f"   Доступно:   {Fore.YELLOW}{avail:.4f} AIX")
    if medals:
        print(f"   🏅 Медали:  {Fore.YELLOW}{medals} (репутация: {rep})")
    print(f"   Публичный:  {w.public_key}")

    sim = _node_get(url, f"/swap/balances/{w.address}")
    if sim and sim.get("balances"):
        print(f"\n   {Fore.CYAN}💱 Токены:")
        for token, bal in sim["balances"].items():
            if bal > 0:
                print(f"      {token}: {bal / config.SATOSHI:.4f}")
    return 0


def cmd_balance(a):
    try: address, label = resolve(a.who, _node_url(a))
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    url = _node_url(a)
    d = _node_get(url, f"/balance/{address}")
    if d:
        print(f"{Fore.CYAN}💰 Баланс {label} (от ноды {url})")
        if d.get("name"): print(f"   AIX-ID:     {Fore.YELLOW}@{d['name']}")
        print(f"   Всего:      {Fore.YELLOW}{d['balance_aix']:.4f} AIX")
        locked = d.get('locked_aix', 0)
        if locked:
            br = d.get('locked_breakdown', {})
            print(f"   Заморожено: {Fore.YELLOW}{locked:.4f} AIX "
                  f"(🎁 {br.get('gift', 0):.2f} + 🕰️ {br.get('timelock', 0):.2f})")
            print(f"   Доступно:   {Fore.YELLOW}{d.get('available_aix', 0):.4f} AIX")
        if d.get("medals_count"):
            print(f"   🏅 Медали:  {Fore.YELLOW}{d['medals_count']} "
                  f"(репутация: {d.get('reputation', 0)})")
    else:
        chain = load_chain()
        bal = chain.get_balance(address) / config.SATOSHI
        print(f"{Fore.CYAN}💰 Баланс {label} (локально)")
        print(f"   Всего:      {Fore.YELLOW}{bal:.4f} AIX")
    return 0


def cmd_mine(a):
    try: address, label = resolve(a.who, _node_url(a))
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    chain = load_chain()
    print(f"{Fore.CYAN}⛏️  Майню локально...")
    cb = Transaction.create_coinbase(recipient=address,
                                     amount=config.INITIAL_BLOCK_REWARD * config.SATOSHI)
    txs = chain.mempool.select_for_block(max_count=100)
    nb = Block(index=chain.height() + 1, timestamp=time.time(),
               transactions=[cb] + txs, previous_hash=chain.last_block().hash)
    start = time.time()
    attempts = nb.mine(difficulty=chain.difficulty)
    elapsed = time.time() - start
    ok, msg = chain.add_block(nb)
    if not ok:
        print(f"{Fore.RED}❌ {msg}"); return 1
    storage.save(chain)
    print(f"{Fore.GREEN}✅ Блок #{nb.index} замайнен за {elapsed:.2f} сек")
    print(f"   {Fore.YELLOW}⚠️  Локальный майнинг пишет в chain.json, не в ноду!")
    return 0


def cmd_send(a):
    chain = load_chain()
    if not Wallet.exists(a.sender):
        print(f"{Fore.RED}❌ Кошелёк '{a.sender}' не найден"); return 1
    w = Wallet.load(a.sender)
    try: recv_addr, recv_label = resolve(a.recipient, _node_url(a))
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    amount = int(a.amount * config.SATOSHI)
    tx = Transaction(sender=w.address, recipient=recv_addr, amount=amount,
                     message=a.message or "")
    w.sign_transaction(tx)
    ok, msg = tx.is_valid()
    if not ok:
        print(f"{Fore.RED}❌ {msg}"); return 1
    ok, msg = chain.mempool.add(tx)
    if not ok:
        print(f"{Fore.RED}❌ {msg}"); return 1
    storage.save(chain)
    print(f"{Fore.GREEN}✅ Транзакция в локальный mempool")
    print(f"   {Fore.CYAN}Используй: aix node send ...")
    return 0


def cmd_chain(a):
    url = _node_url(a)
    d = _node_get(url, "/status")
    if d:
        print(f"{Fore.CYAN}⛓️  Цепочка AIX OS (от ноды {url})")
        print(f"   Высота:     {Fore.YELLOW}{d['height']}")
        print(f"   Транзакций: {Fore.YELLOW}{d['total_transactions']}")
        print(f"   Mempool:    {Fore.YELLOW}{d['mempool_size']}")
        print(f"   Сложность:  {Fore.YELLOW}{d['difficulty']}")
        print(f"   Работа:     {Fore.YELLOW}{d['total_work']}")
        print(f"   Всего AIX:  {Fore.YELLOW}{d['total_supply_aix']:.2f}")
        print(f"   🔥 Сожжено: {Fore.YELLOW}{d.get('total_burned_aix', 0):.2f} AIX")
        print(f"   🏅 Медалей: {Fore.YELLOW}{d.get('sbt_count', 0)}")
        print(f"   🎗️  Наследств: {Fore.YELLOW}{d.get('inheritances_count', 0)}")
        print(f"   🪪 AIX-ID:  {Fore.YELLOW}{d.get('ids_count', 0)}")
        print(f"   🔥 Артефактов: {Fore.YELLOW}{d.get('burn_count', 0)}")
        print(f"   📇 Контактов: {Fore.YELLOW}{d.get('contacts_count', 0)}")
        print(f"   💱 Пулов:    {Fore.YELLOW}{d.get('swap_pools_count', 0)}")
        print(f"   🧬 PoC:      {Fore.YELLOW}{d.get('poc_count', 0)} вкладов, "
              f"фонд: {d.get('poc_pool_aix', 0):.2f} AIX")
        return 0
    chain = load_chain()
    print(f"{Fore.CYAN}⛓️  Цепочка AIX OS (локально)")
    print(f"   Высота:     {Fore.YELLOW}{chain.height()}")
    print(f"   Всего AIX:  {Fore.YELLOW}{chain.total_supply() / config.SATOSHI:.2f}")
    return 0


def cmd_qr(a):
    import qrcode
    try: address, label = resolve(a.who, _node_url(a))
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    qr = qrcode.QRCode(version=1, box_size=1, border=1)
    qr.add_data(address); qr.make(fit=True)
    print(f"{Fore.CYAN}📱 QR для: {Fore.YELLOW}{label}\n")
    qr.print_ascii(invert=True)
    print(f"\n{Fore.CYAN}Адрес: {Fore.YELLOW}{address}")
    if a.png:
        qr2 = qrcode.QRCode(version=1, box_size=10, border=4)
        qr2.add_data(address); qr2.make(fit=True)
        qr2.make_image(fill_color="black", back_color="white").save(a.png)
        print(f"{Fore.GREEN}✅ PNG: {a.png}")
    return 0


# =============================================================================
# NODE
# =============================================================================

def cmd_node_status(a):
    url = _node_url(a)
    d = _node_get(url, "/status")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🖥️  Нода: {Fore.YELLOW}{d.get('self_url', url)}")
    print(f"   Версия:     {d['version']}")
    print(f"   Высота:     {Fore.YELLOW}{d['height']}")
    print(f"   Сложность:  {d['difficulty']}")
    print(f"   Работа:     {Fore.YELLOW}{d.get('total_work', '—')}")
    print(f"   Транзакций: {d['total_transactions']}")
    print(f"   Mempool:    {d['mempool_size']}")
    print(f"   Всего AIX:  {d['total_supply_aix']:.2f}")
    print(f"   🔥 Сожжено: {d.get('total_burned_aix', 0):.2f} AIX")
    print(f"   Пиров:      {Fore.YELLOW}{d['peers_count']}")
    print(f"   🎁 Gift:    {d.get('gifts_active', 0)} / {d.get('gifts_count', 0)}")
    print(f"   🕰️  Lock:    {d.get('timelocks_active', 0)} / {d.get('timelocks_count', 0)}")
    print(f"   🏅 SBT:     {d.get('sbt_count', 0)}")
    print(f"   🎗️  Inherit: {d.get('inheritances_active', 0)} / {d.get('inheritances_count', 0)}")
    print(f"   🪪 IDs:     {d.get('ids_count', 0)}")
    print(f"   🔥 Burn:    {d.get('burn_count', 0)}")
    print(f"   📇 Contacts: {d.get('contacts_count', 0)} / {d.get('contacts_addresses', 0)}")
    print(f"   💱 Swap:    {d.get('swap_pools_count', 0)} пулов")
    print(f"   🧬 PoC:     {d.get('poc_count', 0)} вкладов, фонд: {d.get('poc_pool_aix', 0):.2f} AIX")
    print(f"   Хеш посл.:  {d.get('last_block_hash', '')[:32]}...")
    print(f"   Цепочка OK: {Fore.GREEN + '✅' if d.get('chain_valid') else Fore.RED + '❌'}")
    return 0


def cmd_node_peers(a):
    url = _node_url(a)
    d = _node_get(url, "/peers")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🌐 Пиры {d['self_url']}")
    if not d["peers"]:
        print(f"   {Fore.YELLOW}Нет пиров."); return 0
    rows = []
    for p in d["peers"]:
        status = f"{Fore.GREEN}✅{Fore.RESET}" if p["is_alive"] else f"{Fore.RED}❌{Fore.RESET}"
        rows.append([status, p["url"], p["height"],
                     p.get("total_work", 0), p["difficulty"]])
    print(tabulate(rows, headers=["", "URL", "Height", "Work", "Diff"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_node_connect(a):
    url = _node_url(a)
    try:
        r = requests.post(f"{url}/peers/add",
                          json={"url": a.peer_url.rstrip("/")}, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Пир добавлен: {a.peer_url}")
    print(f"   Всего пиров: {d['peers_count']}")
    return 0


def cmd_node_sync(a):
    url = _node_url(a)
    try:
        r = requests.post(f"{url}/sync/pull", timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    s = d.get("status")
    if s == "no_change":
        print(f"{Fore.CYAN}⏸️  Цепочка актуальна")
    elif s == "replaced":
        print(f"{Fore.GREEN}✅ Синхронизировано: {d['old_height']} → {d['new_height']}")
    elif s == "no_peers":
        print(f"{Fore.YELLOW}⚠️  Нет пиров")
    return 0


def cmd_node_state_pull(a):
    url = _node_url(a)
    try:
        r = requests.post(f"{url}/sync/state/pull", timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ State pull завершён")
    print(f"   Пиров опрошено: {d['peers_asked']}")
    added = d.get("added", {})
    print(f"   Добавлено: 🎁 {added.get('gifts', 0)} | "
          f"🕰️ {added.get('timelocks', 0)} | "
          f"🏅 {added.get('medals', 0)} | "
          f"🎗️ {added.get('inheritances', 0)} | "
          f"🪪 {added.get('aix_ids', 0)} | "
          f"🔥 {added.get('burn_artifacts', 0)} | "
          f"📇 {added.get('contacts', 0)} | "
          f"💱 {added.get('swap_pools', 0)} | "
          f"🧬 {added.get('poc_contributions', 0)}")
    cur = d.get("current", {})
    print(f"   Всего:     🎁 {cur.get('gifts', 0)} | "
          f"🕰️ {cur.get('timelocks', 0)} | "
          f"🏅 {cur.get('medals', 0)} | "
          f"🎗️ {cur.get('inheritances', 0)} | "
          f"🪪 {cur.get('aix_ids', 0)} | "
          f"🔥 {cur.get('burn_artifacts', 0)} | "
          f"📇 {cur.get('contacts', 0)} | "
          f"💱 {cur.get('swap_pools', 0)} | "
          f"🧬 {cur.get('poc_contributions', 0)}")
    return 0


def cmd_node_mine(a):
    url = _node_url(a)
    if not Wallet.exists(a.who):
        print(f"{Fore.RED}❌ Кошелёк '{a.who}' не найден"); return 1
    w = Wallet.load(a.who)
    print(f"{Fore.CYAN}⛏️  Майню через ноду {url}...")
    try:
        r = requests.post(f"{url}/mine",
                          json={"miner_address": w.address, "broadcast": True},
                          timeout=60)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Блок #{d['block_index']} замайнен за {d['time_seconds']} сек")
    print(f"   Hash:    {d['block_hash']}")
    print(f"   Награда: {Fore.YELLOW}+{d['reward_aix']} AIX")
    print(f"   TXs:     {d['transactions_in_block']}")
    color = Fore.GREEN if d['broadcast_to_peers'] > 0 else Fore.YELLOW
    print(f"   Разослано пирам: {color}{d['broadcast_to_peers']}")
    if d.get("lottery"):
        lot = d["lottery"]
        print(f"\n   {Fore.MAGENTA}🎰 СЧАСТЛИВЫЙ БЛОК! 🎰")
        print(f"   Победитель: {lot['winner']}")
        print(f"   Приз:       {Fore.YELLOW}+{lot['prize_aix']} AIX")
    return 0


def cmd_node_send(a):
    url = _node_url(a)
    if not Wallet.exists(a.sender):
        print(f"{Fore.RED}❌ Кошелёк '{a.sender}' не найден"); return 1
    w = Wallet.load(a.sender)
    recv = a.recipient
    recv_label = recv
    if recv.startswith("phone:"):
        print(f"{Fore.CYAN}📇 Ищу номер в AIX Contacts...")
        phone = recv[6:].strip()
        try:
            r = requests.post(f"{url}/contacts/lookup",
                              json={"phone": phone}, timeout=5)
            if r.status_code != 200:
                print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
            lookup = r.json()
            recv_addr = lookup["address"]
            aix_id = lookup.get("aix_id")
            recv_label = f"📇{aix_id or phone} ({recv_addr[:20]}...)"
            print(f"   {Fore.GREEN}✅ Номер найден: {recv_label}")
        except requests.RequestException as e:
            print(f"{Fore.RED}❌ {e}"); return 1
    else:
        try:
            recv_addr, recv_label = resolve(recv, url)
        except ValueError as e:
            print(f"{Fore.RED}❌ {e}"); return 1

    print(f"{Fore.CYAN}📤 Отправляю через ноду {url}...")
    try:
        r = requests.post(f"{url}/send", json={
            "sender": w.address, "recipient": recv_addr,
            "amount": 0, "amount_aix": a.amount,
            "private_key": w.private_key, "message": a.message or "",
        }, timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Транзакция принята")
    print(f"   TX ID:  {d['tx_id'][:32]}...")
    print(f"   Кому:   {recv_label}")
    print(f"   Разослано пирам: {d['broadcast_to_peers']}")
    return 0


# =============================================================================
# GIFT-LINK
# =============================================================================

def cmd_gift_create(a):
    url = _node_url(a)
    if not Wallet.exists(a.sender):
        print(f"{Fore.RED}❌ Кошелёк '{a.sender}' не найден"); return 1
    w = Wallet.load(a.sender)
    print(f"{Fore.CYAN}🎁 Создаю gift через ноду {url}...")
    try:
        r = requests.post(f"{url}/gift/create", json={
            "sender": w.address, "amount_aix": a.amount,
            "ttl_days": a.days, "message": a.message or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Gift-ссылка создана!\n")
    print(f"   {Fore.CYAN}Код:    {Fore.YELLOW}{d['code']}")
    print(f"   {Fore.CYAN}Сумма:  {Fore.YELLOW}{d['amount_aix']} AIX")
    print(f"   {Fore.CYAN}Истекает через: {d['expires_in_days']} дней")
    if d.get('message'): print(f"   {Fore.CYAN}Сообщение: {d['message']}")
    print()
    print(f"   {Fore.GREEN}Скопируй код выше и передай другу:")
    print(f"   {Fore.YELLOW}aix gift claim {d['code']} <имя_кошелька>")
    return 0


def cmd_gift_info(a):
    url = _node_url(a)
    try:
        r = requests.get(f"{url}/gift/{a.code}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🎁 Gift {d['code']}")
    print(f"   Сумма:   {Fore.YELLOW}{d['amount_aix']} AIX")
    print(f"   Статус:  {d['status']}")
    if d.get('message'): print(f"   Msg:     {d['message']}")
    return 0


def cmd_gift_claim(a):
    url = _node_url(a)
    if not Wallet.exists(a.recipient):
        print(f"{Fore.RED}❌ Кошелёк '{a.recipient}' не найден"); return 1
    w = Wallet.load(a.recipient)
    print(f"{Fore.CYAN}🎁 Активирую {a.code} на {a.recipient}...")
    try:
        r = requests.post(f"{url}/gift/{a.code}/claim", json={
            "code": a.code, "recipient": w.address,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Gift активирован!")
    print(f"   TX ID: {d['tx_id'][:32]}...")
    print(f"   {Fore.YELLOW}Замайни блок: aix node mine <майнер>")
    return 0


def cmd_gift_cancel(a):
    url = _node_url(a)
    if not Wallet.exists(a.sender):
        print(f"{Fore.RED}❌ Кошелёк '{a.sender}' не найден"); return 1
    w = Wallet.load(a.sender)
    try:
        r = requests.post(f"{url}/gift/{a.code}/cancel", json={
            "code": a.code, "sender": w.address,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Gift {a.code} отменён")
    return 0


def cmd_gift_list(a):
    url = _node_url(a)
    try: address, label = resolve(a.sender, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    try:
        r = requests.get(f"{url}/gifts/sender/{address}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🎁 Gift-ссылки от {label}: {d['count']}")
    if not d["links"]: return 0
    rows = []
    for l in d["links"]:
        rows.append([l["code"], f"{l['amount_aix']:.2f}",
                     l["status"], l.get("claimed_by", "")[:20]])
    print(tabulate(rows, headers=["Код", "Сумма AIX", "Статус", "Кому"],
                   tablefmt="rounded_outline"))
    return 0


# =============================================================================
# TIME-LOCK
# =============================================================================

def cmd_timelock_create(a):
    url = _node_url(a)
    if not Wallet.exists(a.owner):
        print(f"{Fore.RED}❌ Кошелёк '{a.owner}' не найден"); return 1
    w = Wallet.load(a.owner)
    recipient_addr = ""
    if a.to:
        try: recipient_addr, _ = resolve(a.to, url)
        except ValueError as e:
            print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🕰️  Создаю капсулу через ноду {url}...")
    try:
        r = requests.post(f"{url}/timelock/create", json={
            "owner": w.address, "amount_aix": a.amount,
            "until": a.until, "recipient": recipient_addr,
            "message": a.message or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Капсула создана!\n")
    print(f"   {Fore.CYAN}ID:      {Fore.YELLOW}{d['id']}")
    print(f"   {Fore.CYAN}Сумма:   {Fore.YELLOW}{d['amount_aix']} AIX")
    print(f"   {Fore.CYAN}Открыть: {Fore.YELLOW}{d['unlock_at']}")
    print(f"   {Fore.CYAN}Кому:    {d['recipient']}")
    if d.get('message'): print(f"   {Fore.CYAN}Сообщение: {d['message']}")
    return 0


def cmd_timelock_info(a):
    url = _node_url(a)
    try:
        r = requests.get(f"{url}/timelock/{a.lock_id}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🕰️  Капсула {d['id']}")
    print(f"   Владелец:  {d['owner'][:32]}...")
    print(f"   Получатель: {d['recipient']}")
    print(f"   Сумма:     {Fore.YELLOW}{d['amount_aix']} AIX")
    print(f"   Статус:    {d['status']}")
    print(f"   Открыть:   {d['unlock_at_str']}")
    print(f"   Осталось:  {d['time_left']}")
    if d.get('message'): print(f"   Сообщение: {d['message']}")
    return 0


def cmd_timelock_release(a):
    url = _node_url(a)
    if not Wallet.exists(a.by):
        print(f"{Fore.RED}❌ Кошелёк '{a.by}' не найден"); return 1
    w = Wallet.load(a.by)
    try:
        r = requests.post(f"{url}/timelock/{a.lock_id}/release",
                          json={"lock_id": a.lock_id, "by": w.address},
                          timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Капсула активирована!")
    print(f"   TX ID: {d['tx_id'][:32]}...")
    return 0


def cmd_timelock_cancel(a):
    url = _node_url(a)
    if not Wallet.exists(a.by):
        print(f"{Fore.RED}❌ Кошелёк '{a.by}' не найден"); return 1
    w = Wallet.load(a.by)
    try:
        r = requests.post(f"{url}/timelock/{a.lock_id}/cancel",
                          json={"lock_id": a.lock_id, "by": w.address},
                          timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Капсула {a.lock_id} отменена")
    return 0


def cmd_timelock_list(a):
    url = _node_url(a)
    try: address, label = resolve(a.owner, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    try:
        r = requests.get(f"{url}/timelocks/owner/{address}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🕰️  Капсулы {label}: {d['count']}")
    if not d["locks"]: return 0
    rows = []
    for l in d["locks"]:
        rows.append([l["id"], f"{l['amount_aix']:.2f}",
                     l["status"], l.get("unlock_at_str", ""),
                     l.get("time_left", ""), l.get("recipient", "")[:20]])
    print(tabulate(rows, headers=["ID", "AIX", "Статус", "Открыть", "Осталось", "Кому"],
                   tablefmt="rounded_outline"))
    return 0


# =============================================================================
# SBT
# =============================================================================

def cmd_sbt_catalog(a):
    url = _node_url(a)
    d = _node_get(url, "/sbt/catalog")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🏅 Каталог медалей AIX OS:")
    rows = []
    rarity_emoji = {"common": "⚪", "uncommon": "🟢",
                    "rare": "🔵", "legendary": "🟣"}
    for m in d["medals"]:
        supply = m["max_supply"]
        supply_str = f"{m['issued']}/{supply}" if supply else f"{m['issued']}/∞"
        rows.append([f"{m['emoji']} {m['title']}", m["id"],
                     f"{rarity_emoji.get(m['rarity'], '')} {m['rarity']}",
                     supply_str])
    print(tabulate(rows, headers=["Медаль", "ID", "Редкость", "Выдано"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_sbt_award(a):
    url = _node_url(a)
    if not Wallet.exists(a.issuer):
        print(f"{Fore.RED}❌ Кошелёк '{a.issuer}' не найден"); return 1
    issuer_w = Wallet.load(a.issuer)
    try: owner_addr, owner_label = resolve(a.owner, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🏅 Выдаю медаль {a.medal_id}...")
    try:
        r = requests.post(f"{url}/sbt/award", json={
            "medal_id": a.medal_id, "owner": owner_addr,
            "issuer": issuer_w.address, "reason": a.reason or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Медаль вручена!\n")
    print(f"   {d['emoji']} {d['title']} ({d['medal_id']})")
    print(f"   {Fore.CYAN}Получатель: {owner_label}")
    print(f"   {Fore.CYAN}Выдал:      {a.issuer}")
    if d.get('reason'): print(f"   {Fore.CYAN}За что:     {d['reason']}")
    return 0


def cmd_sbt_list(a):
    url = _node_url(a)
    try: address, label = resolve(a.who, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    d = _node_get(url, f"/sbt/owner/{address}")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🏅 Медали {label}")
    print(f"   Репутация: {Fore.YELLOW}{d['reputation']}")
    print(f"   Медалей:   {Fore.YELLOW}{d['count']}\n")
    if not d["medals"]:
        print(f"   {Fore.YELLOW}Пока ни одной медали."); return 0
    rows = []
    for m in d["medals"]:
        rows.append([f"{m['emoji']} {m['title']}", m["id"],
                     m["rarity"], m.get("reason", "")[:30]])
    print(tabulate(rows, headers=["Медаль", "ID", "Редкость", "За что"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_sbt_revoke(a):
    url = _node_url(a)
    try: owner_addr, _ = resolve(a.owner, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    try:
        r = requests.post(f"{url}/sbt/revoke", json={
            "medal_id": a.medal_id, "owner": owner_addr,
            "reason": a.reason or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Медаль {a.medal_id} отозвана у {a.owner}")
    return 0


def cmd_sbt_leaderboard(a):
    url = _node_url(a)
    d = _node_get(url, "/sbt/leaderboard")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🏆 Топ по репутации")
    if not d["top"]:
        print(f"   {Fore.YELLOW}Пока никого."); return 0
    rows = []
    for i, e in enumerate(d["top"], 1):
        name = e.get("name")
        avatar = e.get("avatar") or ""
        who = f"{avatar}@{name}" if name else f"{e['address'][:24]}..."
        rows.append([i, who, e["reputation"], e["medals"]])
    print(tabulate(rows, headers=["#", "Кто", "Репутация", "Медалей"],
                   tablefmt="rounded_outline"))
    return 0


# =============================================================================
# LOTTERY
# =============================================================================

def cmd_lottery_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/lottery/stats")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🎰 AIX Lottery — статистика")
    print(f"   Шанс победы:   {Fore.YELLOW}{d['chance']}")
    print(f"   Приз:          {Fore.YELLOW}{d['prize_per_win_aix']} AIX")
    print(f"   Всего блоков:  {Fore.YELLOW}{d['total_blocks']}")
    print(f"   Побед:         {Fore.YELLOW}{d['total_wins']}")
    print(f"   Выплачено:     {Fore.YELLOW}{d['total_prize_aix']:.2f} AIX\n")
    if not d["wins"]:
        print(f"   {Fore.YELLOW}Пока никто не выигрывал."); return 0
    rows = []
    for w in d["wins"][-10:]:
        rows.append([w["block"], w["winner"][:32] + "...",
                     f"{w['amount_aix']:.2f}",
                     w["block_hash"][:16] + "..."])
    print(tabulate(rows, headers=["Блок", "Победитель", "AIX", "Хеш"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_lottery_info(a):
    url = _node_url(a)
    d = _node_get(url, "/lottery/info")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🎰 AIX Lottery")
    print(f"   Шанс:  {Fore.YELLOW}{d['chance']}")
    print(f"   Приз:  {Fore.YELLOW}{d['prize_aix']} AIX")
    print(f"   {d['description']}")
    return 0


# =============================================================================
# DMS
# =============================================================================

def _parse_heirs(spec: str, node_url: str):
    heirs = []
    for part in spec.split(","):
        part = part.strip()
        if not part: continue
        if ":" not in part:
            raise ValueError(f"Формат: name:percent (получено '{part}')")
        name, pct_str = part.rsplit(":", 1)
        name = name.strip()
        try: pct = float(pct_str)
        except ValueError:
            raise ValueError(f"Процент должен быть числом, получено '{pct_str}'")
        try: addr, _ = resolve(name, node_url)
        except ValueError as e:
            raise ValueError(f"Не могу разобрать '{name}': {e}")
        heirs.append({"address": addr, "share_percent": pct, "name": name})
    return heirs


def cmd_inherit_create(a):
    url = _node_url(a)
    if not Wallet.exists(a.owner):
        print(f"{Fore.RED}❌ Кошелёк '{a.owner}' не найден"); return 1
    w = Wallet.load(a.owner)
    try: heirs = _parse_heirs(a.heirs, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🎗️  Создаю switch через ноду {url}...")
    try:
        r = requests.post(f"{url}/inherit/create", json={
            "owner": w.address, "heirs": heirs,
            "timeout_days": a.timeout, "note": a.note or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Switch создан!\n")
    print(f"   {Fore.CYAN}ID:        {Fore.YELLOW}{d['id']}")
    print(f"   {Fore.CYAN}Таймаут:   {Fore.YELLOW}{d['timeout_days']} дней")
    print(f"   {Fore.CYAN}Наследники:")
    for h in d["heirs"]:
        print(f"      • {h['name'] or h['address'][:20]} — {h['share_percent']}%")
    if d.get("note"): print(f"   {Fore.CYAN}Записка:   {d['note']}")
    print(f"\n   {Fore.YELLOW}⚠️  Не забывай check-in: aix inherit checkin {a.owner}")
    return 0


def cmd_inherit_info(a):
    url = _node_url(a)
    try:
        r = requests.get(f"{url}/inherit/{a.sid}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    status_color = {"active": Fore.GREEN, "triggerable": Fore.YELLOW,
                    "triggered": Fore.CYAN, "cancelled": Fore.RED}.get(d['status'], Fore.WHITE)
    print(f"{Fore.CYAN}🎗️  Switch {d['id']}")
    print(f"   Владелец:  {d['owner'][:32]}...")
    print(f"   Статус:    {status_color}{d['status']}")
    print(f"   Таймаут:   {d['timeout_days']} дней")
    print(f"   Осталось:  {d['time_left']}")
    print(f"   Наследники:")
    for h in d["heirs"]:
        print(f"      • {h['name'] or h['address'][:20]} — {h['share_percent']}%")
    if d.get('note'): print(f"   Записка:   {d['note']}")
    return 0


def cmd_inherit_checkin(a):
    url = _node_url(a)
    if not Wallet.exists(a.owner):
        print(f"{Fore.RED}❌ Кошелёк '{a.owner}' не найден"); return 1
    w = Wallet.load(a.owner)
    print(f"{Fore.CYAN}🎗️  Check-in через ноду {url}...")
    try:
        r = requests.post(f"{url}/inherit/0000/checkin", json={
            "owner": w.address,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Check-in выполнен")
    print(f"   ID:   {d['id']}")
    print(f"   Msg:  {d['message']}")
    return 0


def cmd_inherit_trigger(a):
    url = _node_url(a)
    if not Wallet.exists(a.heir):
        print(f"{Fore.RED}❌ Кошелёк '{a.heir}' не найден"); return 1
    w = Wallet.load(a.heir)
    print(f"{Fore.CYAN}🎗️  Активирую switch {a.sid}...")
    try:
        r = requests.post(f"{url}/inherit/{a.sid}/trigger",
                          json={"by": w.address}, timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Switch активирован!")
    print(f"   TX: {d['count']} транзакций создано")
    for tid in d["tx_ids"]:
        print(f"      • {tid[:32]}...")
    print(f"   {Fore.YELLOW}Замайни блок: aix node mine <майнер>")
    return 0


def cmd_inherit_cancel(a):
    url = _node_url(a)
    if not Wallet.exists(a.owner):
        print(f"{Fore.RED}❌ Кошелёк '{a.owner}' не найден"); return 1
    w = Wallet.load(a.owner)
    try:
        r = requests.post(f"{url}/inherit/{a.sid}/cancel",
                          json={"by": w.address}, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Switch {a.sid} отменён")
    return 0


def cmd_inherit_list_owner(a):
    url = _node_url(a)
    try: address, label = resolve(a.owner, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    try:
        r = requests.get(f"{url}/inherit/owner/{address}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🎗️  Switch-и {label}: {d['count']}")
    if not d["switches"]: return 0
    rows = []
    for s in d["switches"]:
        heirs_str = ", ".join(f"{h['name'] or h['address'][:8]}:{h['share_percent']:.0f}%"
                              for h in s["heirs"])
        rows.append([s["id"], s["status"], s["time_left"],
                     f"{s['timeout_days']}д", heirs_str[:40]])
    print(tabulate(rows, headers=["ID", "Статус", "Осталось", "Таймаут", "Наследники"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_inherit_list_heir(a):
    url = _node_url(a)
    try: address, label = resolve(a.heir, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    try:
        r = requests.get(f"{url}/inherit/heir/{address}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🎗️  Switch-и, где {label} — наследник: {d['count']}")
    if not d["switches"]: return 0
    rows = []
    for s in d["switches"]:
        my_share = next((h['share_percent'] for h in s["heirs"]
                         if h['address'] == address), 0)
        rows.append([s["id"], s["status"], s["time_left"],
                     f"{s['timeout_days']}д", f"{my_share:.0f}%"])
    print(tabulate(rows, headers=["ID", "Статус", "Осталось", "Таймаут", "Моя доля"],
                   tablefmt="rounded_outline"))
    return 0


# =============================================================================
# AIX-ID
# =============================================================================

def cmd_id_register(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    print(f"{Fore.CYAN}🪪 Регистрирую AIX-ID '{a.name}'...")
    try:
        r = requests.post(f"{url}/id/register", json={
            "address": w.address, "name": a.name,
            "display_name": a.display_name or "",
            "avatar": a.avatar or "👤", "bio": a.bio or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ AIX-ID зарегистрирован!\n")
    print(f"   {d['avatar']} {d['name']} ({d['display_name']})")
    print(f"   {Fore.CYAN}Адрес:  {d['address']}")
    if d.get('bio'): print(f"   {Fore.CYAN}О себе: {d['bio']}")
    print(f"   {Fore.CYAN}Разослано пирам: {d.get('broadcast_to_peers', 0)}")
    return 0


def cmd_id_update(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    print(f"{Fore.CYAN}🪪 Обновляю профиль...")
    try:
        r = requests.post(f"{url}/id/update", json={
            "address": w.address, "display_name": a.display_name,
            "avatar": a.avatar, "bio": a.bio,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Профиль обновлён")
    print(f"   {d['avatar']} {d['name']} ({d['display_name']})")
    return 0


def cmd_id_show(a):
    url = _node_url(a)
    name = a.who.lstrip("@")
    d = _node_get(url, f"/id/{name}")
    if not d:
        try:
            addr, _ = resolve(a.who, url)
            d = _node_get(url, f"/id/{addr}")
        except ValueError: pass
    if not d:
        print(f"{Fore.RED}❌ AIX-ID '{a.who}' не найден"); return 1
    print(f"{Fore.CYAN}🪪 AIX-ID: {d['avatar']} {Fore.YELLOW}{d['name']}")
    if d.get('display_name') and d['display_name'] != d['name']:
        print(f"   Имя:        {d['display_name']}")
    print(f"   Адрес:      {d['address']}")
    if d.get('bio'): print(f"   О себе:     {d['bio']}")
    print(f"   Баланс:     {Fore.YELLOW}{d['balance_aix']:.4f} AIX")
    print(f"   🏅 Медали:  {d['medals_count']} (репутация: {d['reputation']})")
    return 0


def cmd_id_resolve(a):
    url = _node_url(a)
    name = a.who.lstrip("@")
    d = _node_get(url, f"/id/resolve/{name}")
    if not d:
        print(f"{Fore.RED}❌ '{a.who}' не найден"); return 1
    print(f"{Fore.GREEN}✅ {a.who} → {d['address']}")
    return 0


def cmd_id_list(a):
    url = _node_url(a)
    d = _node_get(url, "/ids")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🪪 Все AIX-ID: {d['count']}")
    if not d["profiles"]:
        print(f"   {Fore.YELLOW}Пока никого."); return 0
    rows = []
    for p in d["profiles"]:
        rows.append([f"{p['avatar']} @{p['name']}",
                     p['display_name'][:24] if p['display_name'] != p['name'] else "—",
                     f"{p['balance_aix']:.2f}", p['reputation']])
    print(tabulate(rows, headers=["AIX-ID", "Имя", "Баланс", "Репутация"],
                   tablefmt="rounded_outline"))
    return 0


# =============================================================================
# BURN
# =============================================================================

def cmd_burn_catalog(a):
    url = _node_url(a)
    d = _node_get(url, "/burn/catalog")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🔥 Каталог артефактов Burn-to-Mint:\n")
    rows = []
    for level, info in d["catalog"].items():
        rows.append([f"{info['emoji']} {info['name']}", level,
                     f"{info['price_aix']:,}", info['rarity'], info['issued']])
    print(tabulate(rows, headers=["Артефакт", "Уровень", "Цена AIX", "Редкость", "Выдано"],
                   tablefmt="rounded_outline"))
    print(f"\n   {Fore.CYAN}Всего сожжено: {d.get('total_burned_aix', 0):.2f} AIX")
    return 0


def cmd_burn_mint(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    level = a.level.upper()
    print(f"{Fore.CYAN}🔥 Сжигаю AIX для {level}...")
    try:
        r = requests.post(f"{url}/burn/mint", json={
            "address": w.address, "level": level,
        }, timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    art = d["artifact"]
    print(f"{Fore.GREEN}✅ Артефакт создан!\n")
    print(f"   {art['emoji']} {art['name']}")
    print(f"   {Fore.CYAN}ID:        {Fore.YELLOW}{art['id']}")
    print(f"   {Fore.CYAN}Редкость:  {art['rarity']}")
    print(f"   {Fore.CYAN}Сожжено:   {Fore.YELLOW}{d['burned_aix']} AIX")
    print(f"\n   {Fore.YELLOW}Замайни блок: aix node mine <майнер>")
    return 0


def cmd_burn_list(a):
    url = _node_url(a)
    try: address, label = resolve(a.who, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    d = _node_get(url, f"/burn/owner/{address}")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🔥 Артефакты {label}: {d['count']}")
    if not d["artifacts"]:
        print(f"   {Fore.YELLOW}Пока ничего."); return 0
    rows = []
    for art in d["artifacts"]:
        rows.append([f"{art['emoji']} {art['name']}", art['id'],
                     art['rarity'], f"{art['amount_burned'] / config.SATOSHI:.0f}"])
    print(tabulate(rows, headers=["Артефакт", "ID", "Редкость", "Сожжено AIX"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_burn_info(a):
    url = _node_url(a)
    try:
        r = requests.get(f"{url}/burn/{a.artifact_id}", timeout=5)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}🔥 Артефакт {d['id']}")
    print(f"   {d['emoji']} {d['name']}")
    print(f"   Редкость: {d['rarity']}")
    print(f"   Владелец: {d['owner']}")
    print(f"   Сожжено:  {Fore.YELLOW}{d['amount_burned_aix']} AIX")
    print(f"   {d['description']}")
    return 0


def cmd_burn_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/burn/stats")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🔥 Burn-to-Mint — статистика\n")
    print(f"   Всего артефактов: {Fore.YELLOW}{d['total_artifacts']}")
    print(f"   Всего сожжено:    {Fore.YELLOW}{d['total_burned_aix']:.2f} AIX\n")
    rows = []
    for level, info in d["by_level"].items():
        rows.append([f"{info['emoji']} {info['name']}", f"{info['price_aix']:,}",
                     info['issued'], f"{info['burned_aix']:.0f}"])
    print(tabulate(rows, headers=["Артефакт", "Цена AIX", "Выдано", "Сожжено AIX"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_burn_leaderboard(a):
    url = _node_url(a)
    d = _node_get(url, "/burn/leaderboard")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🏆 Топ коллекционеров Burn-to-Mint")
    if not d["top"]:
        print(f"   {Fore.YELLOW}Пока никого."); return 0
    rows = []
    for i, e in enumerate(d["top"], 1):
        name = e.get("name")
        who = f"@{name}" if name else f"{e['address'][:24]}..."
        rows.append([i, who, e["total"], e["rare"], f"{e['burned_aix']:.0f}"])
    print(tabulate(rows, headers=["#", "Кто", "Всего", "Редких", "Сожжено AIX"],
                   tablefmt="rounded_outline"))
    return 0


# =============================================================================
# CONTACTS
# =============================================================================

def cmd_contacts_register(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    print(f"{Fore.CYAN}📇 Регистрирую номер {a.phone}...")
    try:
        r = requests.post(f"{url}/contacts/register", json={
            "address": w.address, "phone": a.phone, "label": a.label or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Номер зарегистрирован!\n")
    print(f"   {Fore.CYAN}Владелец:   @{w.name}")
    print(f"   {Fore.CYAN}Хеш номера: {d['phone_hash'][:32]}...")
    print(f"\n   {Fore.RED}🔒 Приватность: номер не хранится. Только SHA-256 хеш.")
    return 0


def cmd_contacts_unregister(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    try:
        r = requests.post(f"{url}/contacts/unregister", json={
            "address": w.address, "phone": a.phone,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Номер отвязан")
    return 0


def cmd_contacts_lookup(a):
    url = _node_url(a)
    print(f"{Fore.CYAN}📇 Ищу номер {a.phone} в сети...")
    try:
        r = requests.post(f"{url}/contacts/lookup", json={"phone": a.phone}, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    avatar = d.get("avatar") or "👤"
    name = d.get("aix_id") or "?"
    display = d.get("display_name") or ""
    print(f"{Fore.GREEN}✅ Номер найден!\n")
    print(f"   {avatar} @{name} {f'({display})' if display else ''}")
    print(f"   {Fore.CYAN}Адрес:  {d['address']}")
    if d.get("label"): print(f"   {Fore.CYAN}Метка:  {d['label']}")
    return 0


def cmd_contacts_list(a):
    url = _node_url(a)
    try: address, label = resolve(a.who, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    d = _node_get(url, f"/contacts/owner/{address}")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}📇 Номера {label}: {d['count']}")
    if not d["contacts"]:
        print(f"   {Fore.YELLOW}Нет номеров."); return 0
    rows = []
    for c in d["contacts"]:
        rows.append([c["phone_hash"][:24] + "...", c.get("label") or "—",
                     time.strftime('%Y-%m-%d', time.localtime(c["created_at"]))])
    print(tabulate(rows, headers=["Хеш номера", "Метка", "Создан"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_contacts_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/contacts/stats")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}📇 AIX Contacts — статистика\n")
    print(f"   Всего контактов:      {Fore.YELLOW}{d['total_contacts']}")
    print(f"   Уникальных адресов:   {Fore.YELLOW}{d['unique_addresses']}")
    return 0


# =============================================================================
# SWAP
# =============================================================================

def cmd_swap_tokens(a):
    url = _node_url(a)
    d = _node_get(url, "/swap/tokens")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}💱 Доступные токены:\n")
    rows = []
    for token, info in d["tokens"].items():
        rows.append([f"{info['emoji']} {token}", info['name']])
    print(tabulate(rows, headers=["Тикер", "Название"], tablefmt="rounded_outline"))
    return 0


def cmd_swap_balance(a):
    url = _node_url(a)
    try: address, label = resolve(a.who, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    d = _node_get(url, f"/swap/balances/{address}")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}💱 Балансы {label}")
    bals = d.get("balances", {})
    if not bals:
        print(f"   {Fore.YELLOW}Пусто."); return 0
    rows = []
    for token, bal in bals.items():
        if bal > 0:
            rows.append([token, f"{bal / config.SATOSHI:.4f}"])
    if not rows:
        print(f"   {Fore.YELLOW}Все нулевые."); return 0
    print(tabulate(rows, headers=["Тикер", "Баланс"], tablefmt="rounded_outline"))
    return 0


def cmd_swap_faucet(a):
    url = _node_url(a)
    try: address, label = resolve(a.who, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.CYAN}💱 Faucet {a.token} для {label}...")
    try:
        r = requests.post(f"{url}/swap/faucet", json={
            "address": address, "token": a.token,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Выдано: {d['amount_aix']:.0f} {a.token}")
    print(f"   Новый баланс: {d['balance_after']:.4f}")
    return 0


def cmd_swap_create_pool(a):
    url = _node_url(a)
    if not Wallet.exists(a.creator):
        print(f"{Fore.RED}❌ Кошелёк '{a.creator}' не найден"); return 1
    w = Wallet.load(a.creator)
    print(f"{Fore.CYAN}💱 Создаю пул {a.token_x}/{a.token_y}...")
    try:
        r = requests.post(f"{url}/swap/create_pool", json={
            "creator": w.address,
            "token_x": a.token_x.upper(), "token_y": a.token_y.upper(),
            "amount_x_aix": a.amount_x, "amount_y_aix": a.amount_y,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    p = d["pool"]
    print(f"{Fore.GREEN}✅ Пул создан!\n")
    print(f"   {Fore.CYAN}ID:        {Fore.YELLOW}{p['id']}")
    print(f"   {Fore.CYAN}Резервы:   {p['reserve_a']:.4f} {p['token_a']} + {p['reserve_b']:.4f} {p['token_b']}")
    print(f"   {Fore.CYAN}Курс:      1 {p['token_a']} = {p['price_a_in_b']:.6f} {p['token_b']}")
    print(f"   {Fore.CYAN}LP всего:  {p['total_lp']:.4f}")
    return 0


def cmd_swap_pools(a):
    url = _node_url(a)
    d = _node_get(url, "/swap/pools")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}💱 Пулы ликвидности: {d['count']}")
    if not d["pools"]:
        print(f"   {Fore.YELLOW}Пулов нет."); return 0
    rows = []
    for p in d["pools"]:
        rows.append([p["id"], f"{p['reserve_a']:.2f}", f"{p['reserve_b']:.2f}",
                     f"{p['price_a_in_b']:.6f}", f"{p['total_lp']:.2f}", p["lp_holders"]])
    print(tabulate(rows, headers=["Пул", "Резерв A", "Резерв B", "Курс A→B", "LP", "LP-holders"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_swap_pool_info(a):
    url = _node_url(a)
    d = _node_get(url, f"/swap/pool/{a.pool_id}")
    if not d:
        print(f"{Fore.RED}❌ Пул '{a.pool_id}' не найден"); return 1
    print(f"{Fore.CYAN}💱 Пул {d['id']}")
    print(f"   {Fore.CYAN}Токен A:    {d['token_a']}")
    print(f"   {Fore.CYAN}Токен B:    {d['token_b']}")
    print(f"   {Fore.CYAN}Резерв A:   {Fore.YELLOW}{d['reserve_a']:.4f}")
    print(f"   {Fore.CYAN}Резерв B:   {Fore.YELLOW}{d['reserve_b']:.4f}")
    print(f"   {Fore.CYAN}Курс A→B:   {Fore.YELLOW}{d['price_a_in_b']:.6f}")
    print(f"   {Fore.CYAN}Курс B→A:   {Fore.YELLOW}{d['price_b_in_a']:.6f}")
    print(f"   {Fore.CYAN}LP всего:   {d['total_lp']:.4f}")
    return 0


def cmd_swap_quote(a):
    url = _node_url(a)
    print(f"{Fore.CYAN}💱 Считаю курс...")
    try:
        r = requests.post(f"{url}/swap/quote", json={
            "pool_id": a.pool_id, "from_token": a.from_token.upper(),
            "amount_in_aix": a.amount,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}💱 Курс:\n")
    print(f"   Отдаёте:    {Fore.YELLOW}{d['amount_in_aix']:.4f} {d['from_token']}")
    print(f"   Получите:   {Fore.YELLOW}{d['amount_out_aix']:.4f} {d['to_token']}")
    print(f"   Курс:       1 {d['from_token']} = {d['execution_price']:.6f} {d['to_token']}")
    print(f"   Slippage:   {Fore.YELLOW}{d['slippage_percent']:.4f}%")
    return 0


def cmd_swap_execute(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    print(f"{Fore.CYAN}💱 Обмениваю {a.amount} {a.from_token}...")
    try:
        r = requests.post(f"{url}/swap/execute", json={
            "pool_id": a.pool_id, "address": w.address,
            "from_token": a.from_token.upper(), "amount_in_aix": a.amount,
        }, timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Обмен выполнен!\n")
    print(f"   Отдано:     {Fore.YELLOW}{d['amount_in_aix']:.4f} {d['from_token']}")
    print(f"   Получено:   {Fore.GREEN}{d['amount_out_aix']:.4f} {d['to_token']}")
    print(f"   Slippage:   {d['slippage_percent']:.4f}%")
    return 0


def cmd_swap_add_liq(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    print(f"{Fore.CYAN}💱 Добавляю ликвидность в {a.pool_id}...")
    try:
        r = requests.post(f"{url}/swap/add_liquidity", json={
            "pool_id": a.pool_id, "address": w.address,
            "amount_a_aix": a.amount_a, "amount_b_aix": a.amount_b,
        }, timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Ликвидность добавлена!")
    print(f"   LP-токенов получено: {Fore.YELLOW}{d['lp_tokens_aix']:.4f}")
    return 0


def cmd_swap_remove_liq(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    print(f"{Fore.CYAN}💱 Забираю ликвидность из {a.pool_id}...")
    try:
        r = requests.post(f"{url}/swap/remove_liquidity", json={
            "pool_id": a.pool_id, "address": w.address,
            "lp_amount_aix": a.lp_amount,
        }, timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Ликвидность забрана!")
    print(f"   Получено A: {Fore.YELLOW}{d['amount_a_aix']:.4f}")
    print(f"   Получено B: {Fore.YELLOW}{d['amount_b_aix']:.4f}")
    return 0


def cmd_swap_lp(a):
    url = _node_url(a)
    try: address, label = resolve(a.who, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    d = _node_get(url, f"/swap/lp/{a.pool_id}/{address}")
    if not d:
        print(f"{Fore.RED}❌ Пул не найден"); return 1
    print(f"{Fore.CYAN}💱 LP-позиция {label} в {d['pool_id']}")
    print(f"   LP-токенов:  {Fore.YELLOW}{d['lp_tokens_aix']:.6f}")
    print(f"   Доля:        {Fore.YELLOW}{d['share_percent']:.4f}%")
    print(f"   Стоит A:     {Fore.YELLOW}{d['share_a_aix']:.4f}")
    print(f"   Стоит B:     {Fore.YELLOW}{d['share_b_aix']:.4f}")
    return 0


def cmd_swap_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/swap/stats")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}💱 Swap — статистика\n")
    print(f"   Пулов:      {Fore.YELLOW}{d['total_pools']}")
    print(f"   Держателей: {Fore.YELLOW}{d['total_holders']}\n")
    if d["pools"]:
        rows = []
        for p in d["pools"]:
            rows.append([p["id"], f"{p['reserve_a_aix']:.2f}",
                         f"{p['reserve_b_aix']:.2f}", f"{p['price_a_in_b']:.6f}",
                         f"{p['total_lp']:.2f}"])
        print(tabulate(rows, headers=["Пул", "Резерв A", "Резерв B", "Курс", "LP"],
                       tablefmt="rounded_outline"))
    return 0


# =============================================================================
# POC
# =============================================================================

def cmd_poc_categories(a):
    url = _node_url(a)
    d = _node_get(url, "/poc/categories")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🧬 Категории вклада:\n")
    rows = []
    for code, info in d["categories"].items():
        rows.append([f"{info['emoji']} {code}", info['title']])
    print(tabulate(rows, headers=["Код", "Название"], tablefmt="rounded_outline"))
    return 0


def cmd_poc_pool(a):
    url = _node_url(a)
    d = _node_get(url, "/poc/pool")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🧬 Фонд наград Proof of Contribution\n")
    print(f"   Баланс:      {Fore.YELLOW}{d['balance_aix']:.2f} AIX")
    print(f"   Всего внесли: {d['total_donated_aix']:.2f} AIX")
    print(f"   Всего выплат: {d['total_paid_aix']:.2f} AIX")
    print(f"   Донатов:     {d['donations_count']}")
    print(f"   Выплат:      {d['payouts_count']}")
    return 0


def cmd_poc_donate(a):
    url = _node_url(a)
    if not Wallet.exists(a.wallet):
        print(f"{Fore.RED}❌ Кошелёк '{a.wallet}' не найден"); return 1
    w = Wallet.load(a.wallet)
    print(f"{Fore.CYAN}🧬 Донат {a.amount} AIX в фонд PoC...")
    try:
        r = requests.post(f"{url}/poc/donate", json={
            "address": w.address, "amount_aix": a.amount,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Донат принят!")
    print(f"   TX ID:  {d['tx_id'][:32]}...")
    print(f"   Фонд:   {Fore.YELLOW}{d['pool_balance_aix']:.2f} AIX")
    print(f"\n   {Fore.YELLOW}Замайни блок: aix node mine <майнер>")
    return 0


def cmd_poc_submit(a):
    url = _node_url(a)
    if not Wallet.exists(a.contributor):
        print(f"{Fore.RED}❌ Кошелёк '{a.contributor}' не найден"); return 1
    w = Wallet.load(a.contributor)
    print(f"{Fore.CYAN}🧬 Создаю вклад...")
    try:
        r = requests.post(f"{url}/poc/submit", json={
            "contributor": w.address,
            "category": a.category.upper(),
            "title": a.title,
            "description": a.description,
            "requested_reward_aix": a.reward,
            "proof_url": a.proof or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Вклад создан!\n")
    print(f"   {Fore.CYAN}ID:         {Fore.YELLOW}{d['id']}")
    print(f"   {Fore.CYAN}Категория:  {d['category']}")
    print(f"   {Fore.CYAN}Title:      {d['title']}")
    print(f"   {Fore.CYAN}Награда:    {Fore.YELLOW}{d['reward_aix']} AIX")
    print(f"   {Fore.CYAN}Уровень:    {d['reward_level']}")
    print(f"   {Fore.CYAN}Нужно подтв: {d['required_confirmations']}")
    print(f"\n   {Fore.YELLOW}Другие могут подтвердить: aix poc confirm {d['id']} <имя_кошелька>")
    return 0


def cmd_poc_confirm(a):
    url = _node_url(a)
    if not Wallet.exists(a.reviewer):
        print(f"{Fore.RED}❌ Кошелёк '{a.reviewer}' не найден"); return 1
    w = Wallet.load(a.reviewer)
    print(f"{Fore.CYAN}🧬 Подтверждаю вклад {a.contribution_id}...")
    try:
        r = requests.post(f"{url}/poc/confirm", json={
            "contribution_id": a.contribution_id, "reviewer": w.address,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Подтверждение принято")
    print(f"   Прогресс: {d['confirmations']}/{d['required']}")
    print(f"   Статус:   {d['contribution_status']}")
    if d['contribution_status'] == 'confirmed':
        print(f"\n   {Fore.YELLOW}Вклад подтверждён! Теперь его можно выплатить:")
        print(f"   aix poc pay {a.contribution_id}")
    return 0


def cmd_poc_reject(a):
    url = _node_url(a)
    if not Wallet.exists(a.reviewer):
        print(f"{Fore.RED}❌ Кошелёк '{a.reviewer}' не найден"); return 1
    w = Wallet.load(a.reviewer)
    try:
        r = requests.post(f"{url}/poc/reject", json={
            "contribution_id": a.contribution_id, "reviewer": w.address,
            "reason": a.reason or "",
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Вклад отклонён")
    return 0


def cmd_poc_pay(a):
    url = _node_url(a)
    print(f"{Fore.CYAN}🧬 Выплачиваю награду за {a.contribution_id}...")
    try:
        r = requests.post(f"{url}/poc/pay", json={
            "contribution_id": a.contribution_id,
        }, timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}❌ {r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    print(f"{Fore.GREEN}✅ Награда выплачена!")
    print(f"   TX ID: {d['tx_id'][:32]}...")
    print(f"   Фонд:  {Fore.YELLOW}{d['pool_balance_aix']:.2f} AIX")
    print(f"\n   {Fore.YELLOW}Замайни блок: aix node mine <майнер>")
    return 0


def cmd_poc_info(a):
    url = _node_url(a)
    d = _node_get(url, f"/poc/{a.contribution_id}")
    if not d:
        print(f"{Fore.RED}❌ Вклад не найден"); return 1
    status_color = {"pending": Fore.YELLOW, "confirmed": Fore.GREEN,
                    "paid": Fore.CYAN, "rejected": Fore.RED}.get(d['status'], Fore.WHITE)
    print(f"{Fore.CYAN}🧬 Вклад {d['id']}")
    print(f"   {Fore.CYAN}Автор:       {d['contributor'][:32]}...")
    print(f"   {Fore.CYAN}Категория:   {d['category']}")
    print(f"   {Fore.CYAN}Title:       {d['title']}")
    print(f"   {Fore.CYAN}Description: {d['description'][:80]}...")
    print(f"   {Fore.CYAN}Награда:     {Fore.YELLOW}{d['requested_reward'] / config.SATOSHI:.2f} AIX")
    print(f"   {Fore.CYAN}Уровень:     {d['reward_level']}")
    print(f"   {Fore.CYAN}Статус:      {status_color}{d['status']}")
    print(f"   {Fore.CYAN}Подтверждений: {len(d['confirmations'])}/{d['required_confirmations']}")
    print(f"   {Fore.CYAN}Отказов:      {len(d['rejections'])}")
    if d.get('proof_url'): print(f"   {Fore.CYAN}Proof:       {d['proof_url']}")
    return 0


def cmd_poc_list(a):
    url = _node_url(a)
    try: address, label = resolve(a.who, url)
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    d = _node_get(url, f"/poc/contributor/{address}")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🧬 Вклады {label}: {d['count']}")
    if not d["contributions"]:
        print(f"   {Fore.YELLOW}Нет вкладов."); return 0
    rows = []
    for c in d["contributions"]:
        rows.append([c["id"], c["category"], c["title"][:30],
                     f"{c['requested_reward'] / config.SATOSHI:.2f}",
                     f"{len(c['confirmations'])}/{c['required_confirmations']}",
                     c["status"]])
    print(tabulate(rows, headers=["ID", "Кат.", "Title", "AIX", "Подтв.", "Статус"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_poc_pending(a):
    url = _node_url(a)
    d = _node_get(url, "/poc/status/pending")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🧬 Ожидают подтверждения: {d['count']}")
    if not d["contributions"]:
        print(f"   {Fore.YELLOW}Нет."); return 0
    rows = []
    for c in d["contributions"]:
        rows.append([c["id"], c["category"], c["title"][:35],
                     f"{c['requested_reward'] / config.SATOSHI:.2f}",
                     f"{len(c['confirmations'])}/{c['required_confirmations']}"])
    print(tabulate(rows, headers=["ID", "Кат.", "Title", "AIX", "Подтв."],
                   tablefmt="rounded_outline"))
    print(f"\n   {Fore.YELLOW}Подтвердить: aix poc confirm <ID> <имя_ревьюера>")
    return 0


def cmd_poc_confirmed(a):
    url = _node_url(a)
    d = _node_get(url, "/poc/confirmed")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🧬 Подтверждены, ждут выплаты: {d['count']}")
    if not d["contributions"]:
        print(f"   {Fore.YELLOW}Нет."); return 0
    rows = []
    for c in d["contributions"]:
        rows.append([c["id"], c["contributor"][:20] + "...", c["title"][:30],
                     f"{c['requested_reward'] / config.SATOSHI:.2f}"])
    print(tabulate(rows, headers=["ID", "Автор", "Title", "AIX"],
                   tablefmt="rounded_outline"))
    print(f"\n   {Fore.YELLOW}Выплатить: aix poc pay <ID>")
    return 0


def cmd_poc_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/poc/stats")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🧬 Proof of Contribution — статистика\n")
    print(f"   Фонд:           {Fore.YELLOW}{d['pool_balance_aix']:.2f} AIX")
    print(f"   Всего внесли:    {d['total_donated_aix']:.2f} AIX")
    print(f"   Всего выплат:    {d['total_paid_aix']:.2f} AIX")
    print(f"   Всего вкладов:  {Fore.YELLOW}{d['total_contributions']}")
    print(f"   Донатов:        {d['donations_count']}")
    print(f"   Выплат:         {d['payouts_count']}\n")
    if d.get("by_status"):
        print(f"   {Fore.CYAN}По статусу:")
        for status, count in d["by_status"].items():
            print(f"      {status}: {count}")
    if d.get("by_category"):
        print(f"\n   {Fore.CYAN}По категории:")
        for cat, count in d["by_category"].items():
            print(f"      {cat}: {count}")
    return 0


def cmd_poc_leaderboard(a):
    url = _node_url(a)
    d = _node_get(url, "/poc/leaderboard")
    if not d:
        print(f"{Fore.RED}❌ Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}🏆 Топ контрибьюторов PoC")
    if not d["top"]:
        print(f"   {Fore.YELLOW}Пока никого."); return 0
    rows = []
    for i, e in enumerate(d["top"], 1):
        name = e.get("name")
        avatar = e.get("avatar") or ""
        who = f"{avatar}@{name}" if name else f"{e['address'][:24]}..."
        rows.append([i, who, e["contributions"], f"{e['reward_aix']:.2f}", e["paid"]])
    print(tabulate(rows, headers=["#", "Кто", "Вкладов", "Награда AIX", "Выплачено"],
                   tablefmt="rounded_outline"))
    return 0


# =============================================================================
# AI MEMORY (#AI-1)
# =============================================================================

def _ai_memory_manager():
    return AIMemoryManager(config.DATA_DIR / "ai_memory.json")


def cmd_ai_remember(a):
    mgr = _ai_memory_manager()
    try:
        mem = mgr.add(text=a.text, kind=a.kind, priority=a.priority,
                      tags=a.tags, session=a.session, chain_ref=a.chain_ref or "")
    except ValueError as e:
        print(f"{Fore.RED}❌ {e}"); return 1
    ke = KIND_EMOJI.get(mem.kind, "•")
    pe = PRIORITY_EMOJI.get(mem.priority, "•")
    print(f"{Fore.GREEN}✅ Записано: {ke} [{mem.kind}] {pe} {mem.priority}")
    print(f"   {mem.text}")
    print(f"   session={mem.session} ts={mem.ts} hash={mem.hash[:10]}")
    print(f"   всего в памяти: {mgr.count()}")
    return 0


def cmd_ai_brief(a):
    mgr = _ai_memory_manager()
    text = mgr.brief(max_critical=a.critical, max_latest=a.latest)
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8")
        print(f"{Fore.GREEN}✅ Бриф записан: {a.output} ({len(text)} символов)")
    else:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
        print(text)
    return 0


def cmd_ai_stats(a):
    mgr = _ai_memory_manager()
    st = mgr.stats()
    print(f"{Fore.CYAN}🧠 AI Memory — статистика")
    print(f"   Всего:      {Fore.YELLOW}{st['total']}")
    print(f"   Сессий:     {Fore.YELLOW}{st['sessions']}")
    print(f"   По типам:   {st['by_kind']}")
    print(f"   Приоритеты: {st['by_priority']}")
    return 0


def cmd_ai_list(a):
    mgr = _ai_memory_manager()
    if a.kind:
        memories = mgr.by_kind(a.kind)
    elif a.tag:
        memories = mgr.by_tag(a.tag)
    elif a.session:
        memories = [m for m in mgr.all() if m.session == a.session]
    else:
        memories = mgr.latest(a.limit)
    if not memories:
        print(f"{Fore.YELLOW}Пусто"); return 0
    rows = []
    for m in memories:
        ke = KIND_EMOJI.get(m.kind, "•")
        pe = PRIORITY_EMOJI.get(m.priority, "•")
        tags = ",".join(m.tags) if m.tags else ""
        rows.append([ke, m.kind, pe, m.priority, m.text[:40], m.session, tags])
    print(tabulate(rows, headers=["", "Kind", "", "Prio", "Text", "Session", "Tags"],
                   tablefmt="rounded_outline"))
    return 0

# =============================================================================
# DAO (#13)
# =============================================================================

def cmd_dao_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/dao/stats")
    if not d:
        print(f"{Fore.RED}Node {url} not responding"); return 1
    print(f"{Fore.CYAN}DAO -- statistics")
    print(f"   Total:        {Fore.YELLOW}{d['total']}")
    print(f"   Reputation:   {Fore.YELLOW}{d['total_reputation']}")
    print(f"   Quorum:       {d['quorum_percent']}%")
    print(f"   Pass:         >{d['pass_threshold']}%")
    print(f"   Voting:       {d['voting_blocks']} blocks")
    print(f"   Exec delay:   {d['execution_delay_blocks']} blocks")
    if d.get("by_status"):
        print(f"   By status:    {d['by_status']}")
    return 0


def cmd_dao_list(a):
    url = _node_url(a)
    d = _node_get(url, "/dao/all")
    if not d:
        print(f"{Fore.RED}Node {url} not responding"); return 1
    print(f"{Fore.CYAN}DAO -- proposals: {len(d['proposals'])}")
    if not d["proposals"]:
        print(f"   {Fore.YELLOW}No proposals yet"); return 0
    rows = []
    for p in d["proposals"]:
        rows.append([p["id"], p["kind"], p["status"],
                     p["title"][:40],
                     p["author"][:20] + "..."])
    print(tabulate(rows, headers=["ID", "Kind", "Status", "Title", "Author"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_dao_show(a):
    url = _node_url(a)
    d = _node_get(url, f"/dao/{a.proposal_id}")
    if not d:
        print(f"{Fore.RED}Proposal not found"); return 1
    print(f"{Fore.CYAN}DAO {d['id']}")
    print(f"   Kind:      {d['kind']}")
    print(f"   Status:    {Fore.YELLOW}{d['status']}")
    print(f"   Author:    {d['author']}")
    print(f"   Title:     {d['title']}")
    print(f"   Desc:      {d['description'][:80]}")
    yes_w = sum(v["weight"] for v in d["votes"].values() if v["choice"] == "yes")
    no_w = sum(v["weight"] for v in d["votes"].values() if v["choice"] == "no")
    print(f"   Yes/No:    {Fore.GREEN}{yes_w}{Fore.RESET} / {Fore.RED}{no_w}{Fore.RESET}")
    print(f"   Votes:     {len(d['votes'])}")
    print(f"   Voting end: block {d['voting_ends_at_height']}")
    return 0


def cmd_dao_create(a):
    url = _node_url(a)
    if not Wallet.exists(a.author):
        print(f"{Fore.RED}Wallet {a.author} not found"); return 1
    w = Wallet.load(a.author)
    payload = {}
    if a.kind.upper() == "SPEND":
        if not a.contribution:
            print(f"{Fore.RED}SPEND requires --contribution <id>"); return 1
        payload["contribution_id"] = a.contribution
    try:
        r = requests.post(f"{url}/dao/create", json={
            "author": w.address,
            "title": a.title,
            "description": a.description,
            "kind": a.kind.upper(),
            "payload": payload,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Proposal created: {d['id']}")
    print(f"   Title:      {d['title']}")
    print(f"   Voting end: block {d['voting_ends_at_height']}")
    print(f"\n   Vote: aix dao vote {d['id']} <wallet> yes|no")
    return 0


def cmd_dao_vote(a):
    url = _node_url(a)
    if not Wallet.exists(a.voter):
        print(f"{Fore.RED}Wallet {a.voter} not found"); return 1
    w = Wallet.load(a.voter)
    try:
        r = requests.post(f"{url}/dao/{a.proposal_id}/vote", json={
            "voter": w.address,
            "choice": a.choice,
        }, timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Vote accepted")
    print(f"   Yes: {d['yes_weight']}, No: {d['no_weight']}, Votes: {d['votes_count']}")
    return 0


def cmd_dao_tally(a):
    url = _node_url(a)
    try:
        r = requests.post(f"{url}/dao/{a.proposal_id}/tally", timeout=10)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Tallied: {d['proposal_status']}")
    print(f"   Yes: {d['yes_weight']}, No: {d['no_weight']}")
    return 0


def cmd_dao_execute(a):
    url = _node_url(a)
    try:
        r = requests.post(f"{url}/dao/{a.proposal_id}/execute", timeout=15)
        if r.status_code != 200:
            print(f"{Fore.RED}{r.json().get('detail', r.text)}"); return 1
        d = r.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}{e}"); return 1
    print(f"{Fore.GREEN}Executed: {d['proposal_status']}")
    if d.get("tx_id"):
        print(f"   TX: {d['tx_id'][:32]}...")
    return 0


# =============================================================================
# BRAIN (AI-напарник)
# =============================================================================

def cmd_brain_health(a):
    from ai.brain import BrainAgent
    agent = BrainAgent()
    h = agent.health()
    print(f"{Fore.CYAN}\U0001f9e0 AIX Brain -- health")
    ok = h["backend_available"]
    c = Fore.GREEN if ok else Fore.RED
    print(f"   Backend:   {c}{'OK' if ok else 'DOWN'}{Fore.RESET} {h['backend_url']}")
    print(f"   Model:     {Fore.YELLOW}{h['model']}")
    mk = h["model_installed"]
    cm = Fore.GREEN if mk else Fore.YELLOW
    print(f"   Installed: {cm}{mk}{Fore.RESET}")
    if h.get("models_available"):
        shown = ", ".join(h["models_available"][:5])
        print(f"   Models:    {shown}")
    mem = h["memory_available"]
    print(f"   Memory:    {Fore.GREEN + 'OK' if mem else Fore.RED + 'NO'}{Fore.RESET}")
    print(f"   Node URL:  {h['node_url']}")
    print(f"   Tools:     {', '.join(h['tools'])}")
    return 0 if ok else 1


def cmd_brain_ask(a):
    from ai.brain import BrainAgent, BrainConfig, CLISigner, NullSigner
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    signer = CLISigner(a.wallet, cfg.node_url) if getattr(a, "wallet", None) else NullSigner()
    agent = BrainAgent(cfg, signer=signer)
    if not agent.client.is_available():
        print(f"{Fore.RED}\u274c Ollama недоступен на {cfg.base_url}")
        print(f"   Установи: https://ollama.com")
        print(f"   Затем:    ollama pull {cfg.model}")
        return 1
    print(f"{Fore.CYAN}\U0001f9e0 Brain думает ({cfg.model})...")
    try:
        answer = agent.ask(a.message)
    except Exception as e:
        print(f"{Fore.RED}\u274c {e}")
        return 1
    print(f"{Fore.GREEN}\U0001f4ac {answer}")
    return 0


def cmd_brain_remember(a):
    from ai.brain import BrainAgent
    agent = BrainAgent()
    tags = [t.strip() for t in (a.tags or "").split(",") if t.strip()]
    res = agent.remember(
        title=a.title, kind=a.kind, priority=a.priority,
        body=a.body or "", tags=tags or None,
    )
    if not res.get("ok"):
        print(f"{Fore.RED}\u274c {res.get('error', 'unknown')}")
        return 1
    print(f"{Fore.GREEN}\u2705 Записано в AI Memory")
    print(f"   {a.title}")
    return 0


def cmd_brain_chat(a):
    from ai.brain import BrainAgent, BrainConfig, CLISigner, NullSigner
    cfg = BrainConfig.from_env()
    if a.model:
        cfg = cfg.with_model(a.model)
    signer = CLISigner(a.wallet, cfg.node_url) if getattr(a, "wallet", None) else NullSigner()
    agent = BrainAgent(cfg, signer=signer)
    if not agent.client.is_available():
        print(f"{Fore.RED}\u274c Ollama недоступен на {cfg.base_url}")
        print(f"   Установи: https://ollama.com")
        print(f"   Затем:    ollama pull {cfg.model}")
        return 1
    print(f"{Fore.MAGENTA}\U0001f9e0 AIX Brain -- интерактивный режим ({cfg.model})")
    print(f"   {Fore.YELLOW}exit | quit | stop | выход -- выход, "
          f"reset -- очистить историю{Fore.RESET}")
    while True:
        try:
            line = input(f"{Fore.CYAN}вы> {Fore.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        # Strip leading '>' or '>>' — привычка писать как в REPL
        while line.startswith(">"):
            line = line[1:].lstrip()
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q", "stop", "выход"):
            break
        if line.lower() == "reset":
            agent.reset()
            print(f"{Fore.YELLOW}История очищена.{Fore.RESET}")
            continue
        try:
            answer = agent.ask(line)
        except Exception as e:
            print(f"{Fore.RED}\u274c {e}")
            continue
        if not answer or not answer.strip():
            print(f"{Fore.YELLOW}\U0001f9e0 (пустой ответ модели — история сброшена, "
                  f"попробуй переформулировать){Fore.RESET}")
            continue
        print(f"{Fore.GREEN}\U0001f9e0 {answer}\n")
    return 0


# =============================================================================
# BRAIN SEND -- отправка AIX через CLI
# =============================================================================

def cmd_brain_send(a):
    from ai.brain import BrainTools, BrainConfig, CLISigner
    cfg = BrainConfig.from_env()
    signer = CLISigner(a.wallet, cfg.node_url)
    tools = BrainTools(cfg, signer=signer)
    res = tools.safe_send(a.recipient, a.amount, a.message or "")
    if res.get("ok"):
        print(f"{Fore.GREEN}\u2705 Отправлено")
        print(f"   TX ID: {res.get('tx_id', '')[:32]}...")
        print(f"   Разослано пирам: {res.get('broadcast_to_peers', 0)}")
        return 0
    if res.get("cancelled"):
        print(f"{Fore.YELLOW}\u26a0\ufe0f  Отменено пользователем")
        return 0
    print(f"{Fore.RED}\u274c {res.get('error', 'не отправлено')}")
    return 1


# =============================================================================
# FAUCET
# =============================================================================

def _faucet_path(port: int = 8010) -> str:
    import config as _cfg
    return str(_cfg.DATA_DIR / f"faucet_{port}.json")


def cmd_faucet_stats(a):
    url = _node_url(a)
    d = _node_get(url, "/faucet/stats")
    if not d:
        print(f"{Fore.RED}Нода {url} не отвечает"); return 1
    print(f"{Fore.CYAN}AIX Faucet -- статистика")
    print(f"   Казначей:        {Fore.YELLOW}{d.get('treasury') or '(не назначен)'}")
    print(f"   Выдача:          {Fore.YELLOW}{d.get('amount_per_claim_aix')} AIX")
    print(f"   Cooldown IP:     {d.get('cooldown_ip_hours')} ч")
    print(f"   Лимит/час:       {d.get('hourly_limit')}")
    print(f"   Всего выдач:     {Fore.YELLOW}{d.get('total_claims', 0)}")
    print(f"   Всего отдано:    {Fore.YELLOW}{d.get('total_sent_aix', 0)} AIX")
    print(f"   За последний час: {d.get('claims_last_hour', 0)}")
    print(f"   За 24 часа:       {d.get('claims_last_24h', 0)}")
    return 0


def cmd_faucet_log(a):
    url = _node_url(a)
    limit = getattr(a, "limit", 50) or 50
    d = _node_get(url, f"/faucet/log?limit={limit}")
    if not d:
        print(f"{Fore.RED}Нода {url} не отвечает"); return 1
    entries = d.get("entries", [])
    print(f"{Fore.CYAN}AIX Faucet -- журнал (последние {len(entries)}):")
    if not entries:
        print(f"   {Fore.YELLOW}Пока пусто.")
        return 0
    rows = []
    for e in entries:
        rows.append([
            time.strftime("%Y-%m-%d %H:%M", time.localtime(e.get("ts", 0))),
            (e.get("address", "")[:24] + "...") if len(e.get("address", "")) > 24 else e.get("address", ""),
            e.get("amount_aix", 0),
            (e.get("tx_id", "")[:16] + "...") if e.get("tx_id") else "",
        ])
    print(tabulate(rows, headers=["Время", "Адрес", "AIX", "TX"],
                   tablefmt="rounded_outline"))
    return 0


def cmd_faucet_set_treasury(a):
    import config as _cfg
    path = _cfg.DATA_DIR / "faucet_8010.json"
    mgr = FaucetManager(path)
    mgr.set_treasury(a.wallet)
    print(f"{Fore.GREEN}Казначей назначен: {a.wallet}")
    print(f"   Файл: {path}")
    print(f"   {Fore.YELLOW}Не забудь перезапустить ноды, чтобы казначей подхватился.")
    return 0


# =============================================================================
# ГЛАВНАЯ
# =============================================================================

def main():
    p = argparse.ArgumentParser(prog="aix",
                                description=f"{config.PROJECT_NAME} — {config.PROJECT_TAGLINE}")
    p.add_argument("--version", action="version",
                   version=f"{config.PROJECT_NAME} v{config.VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    # wallet
    pw = sub.add_parser("wallet"); pw.add_argument("--node", default=None)
    wsub = pw.add_subparsers(dest="wallet_cmd", required=True)
    p1 = wsub.add_parser("new"); p1.add_argument("name"); p1.set_defaults(func=cmd_wallet_new)
    p2 = wsub.add_parser("list"); p2.set_defaults(func=cmd_wallet_list)
    p3 = wsub.add_parser("show"); p3.add_argument("name"); p3.set_defaults(func=cmd_wallet_show)

    pb = sub.add_parser("balance"); pb.add_argument("who"); pb.add_argument("--node", default=None)
    pb.set_defaults(func=cmd_balance)

    pm = sub.add_parser("mine"); pm.add_argument("who"); pm.set_defaults(func=cmd_mine)

    ps = sub.add_parser("send")
    ps.add_argument("sender"); ps.add_argument("recipient")
    ps.add_argument("amount", type=float); ps.add_argument("--message", "-m", default="")
    ps.set_defaults(func=cmd_send)

    pc = sub.add_parser("chain"); pc.add_argument("--node", default=None)
    pc.add_argument("--limit", "-l", type=int, default=10); pc.set_defaults(func=cmd_chain)

    pq = sub.add_parser("qr"); pq.add_argument("who"); pq.add_argument("--png")
    pq.set_defaults(func=cmd_qr)

    # node
    pn = sub.add_parser("node"); pn.add_argument("--node", default=DEFAULT_NODE)
    nsub = pn.add_subparsers(dest="node_cmd", required=True)
    nsub.add_parser("status").set_defaults(func=cmd_node_status)
    nsub.add_parser("peers").set_defaults(func=cmd_node_peers)
    pnc = nsub.add_parser("connect"); pnc.add_argument("peer_url")
    pnc.set_defaults(func=cmd_node_connect)
    nsub.add_parser("sync").set_defaults(func=cmd_node_sync)
    nsub.add_parser("state-pull").set_defaults(func=cmd_node_state_pull)
    pnm = nsub.add_parser("mine"); pnm.add_argument("who"); pnm.set_defaults(func=cmd_node_mine)
    pnsend = nsub.add_parser("send")
    pnsend.add_argument("sender"); pnsend.add_argument("recipient")
    pnsend.add_argument("amount", type=float); pnsend.add_argument("--message", "-m", default="")
    pnsend.set_defaults(func=cmd_node_send)

    # gift
    pg = sub.add_parser("gift"); pg.add_argument("--node", default=DEFAULT_NODE)
    gsub = pg.add_subparsers(dest="gift_cmd", required=True)
    pgc = gsub.add_parser("create"); pgc.add_argument("sender"); pgc.add_argument("amount", type=float)
    pgc.add_argument("--days", type=int, default=30); pgc.add_argument("--message", "-m", default="")
    pgc.set_defaults(func=cmd_gift_create)
    pgi = gsub.add_parser("info"); pgi.add_argument("code"); pgi.set_defaults(func=cmd_gift_info)
    pgcl = gsub.add_parser("claim"); pgcl.add_argument("code"); pgcl.add_argument("recipient")
    pgcl.set_defaults(func=cmd_gift_claim)
    pgcn = gsub.add_parser("cancel"); pgcn.add_argument("code"); pgcn.add_argument("sender")
    pgcn.set_defaults(func=cmd_gift_cancel)
    pgl = gsub.add_parser("list"); pgl.add_argument("sender"); pgl.set_defaults(func=cmd_gift_list)

    # timelock
    ptl = sub.add_parser("timelock", aliases=["lock"]); ptl.add_argument("--node", default=DEFAULT_NODE)
    tlsub = ptl.add_subparsers(dest="timelock_cmd", required=True)
    tlc = tlsub.add_parser("create"); tlc.add_argument("owner"); tlc.add_argument("amount", type=float)
    tlc.add_argument("--until", required=True); tlc.add_argument("--to", default=None)
    tlc.add_argument("--message", "-m", default=""); tlc.set_defaults(func=cmd_timelock_create)
    tli = tlsub.add_parser("info"); tli.add_argument("lock_id"); tli.set_defaults(func=cmd_timelock_info)
    tlr = tlsub.add_parser("release"); tlr.add_argument("lock_id"); tlr.add_argument("by")
    tlr.set_defaults(func=cmd_timelock_release)
    tlcn = tlsub.add_parser("cancel"); tlcn.add_argument("lock_id"); tlcn.add_argument("by")
    tlcn.set_defaults(func=cmd_timelock_cancel)
    tll = tlsub.add_parser("list"); tll.add_argument("owner"); tll.set_defaults(func=cmd_timelock_list)

    # sbt
    psbt = sub.add_parser("sbt"); psbt.add_argument("--node", default=DEFAULT_NODE)
    ssub = psbt.add_subparsers(dest="sbt_cmd", required=True)
    ssub.add_parser("catalog").set_defaults(func=cmd_sbt_catalog)
    sa = ssub.add_parser("award"); sa.add_argument("medal_id"); sa.add_argument("owner")
    sa.add_argument("--issuer", required=True); sa.add_argument("--reason", "-r", default="")
    sa.set_defaults(func=cmd_sbt_award)
    sl = ssub.add_parser("list"); sl.add_argument("who"); sl.set_defaults(func=cmd_sbt_list)
    sr = ssub.add_parser("revoke"); sr.add_argument("medal_id"); sr.add_argument("owner")
    sr.add_argument("--reason", "-r", default=""); sr.set_defaults(func=cmd_sbt_revoke)
    ssub.add_parser("leaderboard").set_defaults(func=cmd_sbt_leaderboard)

    # lottery
    plot = sub.add_parser("lottery"); plot.add_argument("--node", default=DEFAULT_NODE)
    lsub = plot.add_subparsers(dest="lottery_cmd", required=True)
    lsub.add_parser("stats").set_defaults(func=cmd_lottery_stats)
    lsub.add_parser("info").set_defaults(func=cmd_lottery_info)

    # inherit
    pinh = sub.add_parser("inherit"); pinh.add_argument("--node", default=DEFAULT_NODE)
    isub = pinh.add_subparsers(dest="inherit_cmd", required=True)
    ic = isub.add_parser("create"); ic.add_argument("owner")
    ic.add_argument("--heirs", required=True); ic.add_argument("--timeout", type=int, default=365)
    ic.add_argument("--note", "-n", default=""); ic.set_defaults(func=cmd_inherit_create)
    ii = isub.add_parser("info"); ii.add_argument("sid"); ii.set_defaults(func=cmd_inherit_info)
    ichk = isub.add_parser("checkin"); ichk.add_argument("owner"); ichk.set_defaults(func=cmd_inherit_checkin)
    itr = isub.add_parser("trigger"); itr.add_argument("sid"); itr.add_argument("heir")
    itr.set_defaults(func=cmd_inherit_trigger)
    icn = isub.add_parser("cancel"); icn.add_argument("sid"); icn.add_argument("owner")
    icn.set_defaults(func=cmd_inherit_cancel)
    ilo = isub.add_parser("list-owner"); ilo.add_argument("owner"); ilo.set_defaults(func=cmd_inherit_list_owner)
    ilh = isub.add_parser("list-heir"); ilh.add_argument("heir"); ilh.set_defaults(func=cmd_inherit_list_heir)

    # id
    pid = sub.add_parser("id"); pid.add_argument("--node", default=DEFAULT_NODE)
    isub2 = pid.add_subparsers(dest="id_cmd", required=True)
    ir = isub2.add_parser("register"); ir.add_argument("wallet"); ir.add_argument("name")
    ir.add_argument("--display-name", "-d", default=None); ir.add_argument("--avatar", "-a", default=None)
    ir.add_argument("--bio", "-b", default=None); ir.set_defaults(func=cmd_id_register)
    iu = isub2.add_parser("update"); iu.add_argument("wallet")
    iu.add_argument("--display-name", "-d", default=None); iu.add_argument("--avatar", "-a", default=None)
    iu.add_argument("--bio", "-b", default=None); iu.set_defaults(func=cmd_id_update)
    ish = isub2.add_parser("show"); ish.add_argument("who"); ish.set_defaults(func=cmd_id_show)
    irs = isub2.add_parser("resolve"); irs.add_argument("who"); irs.set_defaults(func=cmd_id_resolve)
    isub2.add_parser("list").set_defaults(func=cmd_id_list)

    # burn
    pburn = sub.add_parser("burn"); pburn.add_argument("--node", default=DEFAULT_NODE)
    bsub = pburn.add_subparsers(dest="burn_cmd", required=True)
    bsub.add_parser("catalog").set_defaults(func=cmd_burn_catalog)
    bm = bsub.add_parser("mint"); bm.add_argument("wallet"); bm.add_argument("level")
    bm.set_defaults(func=cmd_burn_mint)
    bl = bsub.add_parser("list"); bl.add_argument("who"); bl.set_defaults(func=cmd_burn_list)
    bi = bsub.add_parser("info"); bi.add_argument("artifact_id"); bi.set_defaults(func=cmd_burn_info)
    bsub.add_parser("stats").set_defaults(func=cmd_burn_stats)
    bsub.add_parser("leaderboard").set_defaults(func=cmd_burn_leaderboard)

    # contacts
    pct = sub.add_parser("contacts", aliases=["c"]); pct.add_argument("--node", default=DEFAULT_NODE)
    csub = pct.add_subparsers(dest="contacts_cmd", required=True)
    cr = csub.add_parser("register"); cr.add_argument("wallet"); cr.add_argument("phone")
    cr.add_argument("--label", "-l", default=""); cr.set_defaults(func=cmd_contacts_register)
    cu = csub.add_parser("unregister"); cu.add_argument("wallet"); cu.add_argument("phone")
    cu.set_defaults(func=cmd_contacts_unregister)
    cl = csub.add_parser("lookup"); cl.add_argument("phone"); cl.set_defaults(func=cmd_contacts_lookup)
    cls = csub.add_parser("list"); cls.add_argument("who"); cls.set_defaults(func=cmd_contacts_list)
    csub.add_parser("stats").set_defaults(func=cmd_contacts_stats)

    # swap
    psw = sub.add_parser("swap"); psw.add_argument("--node", default=DEFAULT_NODE)
    ssw = psw.add_subparsers(dest="swap_cmd", required=True)
    ssw.add_parser("tokens").set_defaults(func=cmd_swap_tokens)
    sb = ssw.add_parser("balance"); sb.add_argument("who"); sb.set_defaults(func=cmd_swap_balance)
    sf = ssw.add_parser("faucet"); sf.add_argument("who"); sf.add_argument("token")
    sf.set_defaults(func=cmd_swap_faucet)
    scp = ssw.add_parser("create-pool"); scp.add_argument("creator")
    scp.add_argument("token_x"); scp.add_argument("token_y")
    scp.add_argument("amount_x", type=float); scp.add_argument("amount_y", type=float)
    scp.set_defaults(func=cmd_swap_create_pool)
    ssw.add_parser("pools").set_defaults(func=cmd_swap_pools)
    spi = ssw.add_parser("pool-info"); spi.add_argument("pool_id"); spi.set_defaults(func=cmd_swap_pool_info)
    sq = ssw.add_parser("quote"); sq.add_argument("pool_id"); sq.add_argument("from_token")
    sq.add_argument("amount", type=float); sq.set_defaults(func=cmd_swap_quote)
    se = ssw.add_parser("execute"); se.add_argument("wallet"); se.add_argument("pool_id")
    se.add_argument("from_token"); se.add_argument("amount", type=float); se.set_defaults(func=cmd_swap_execute)
    sal = ssw.add_parser("add-liquidity"); sal.add_argument("wallet"); sal.add_argument("pool_id")
    sal.add_argument("amount_a", type=float); sal.add_argument("amount_b", type=float)
    sal.set_defaults(func=cmd_swap_add_liq)
    srl = ssw.add_parser("remove-liquidity"); srl.add_argument("wallet"); srl.add_argument("pool_id")
    srl.add_argument("lp_amount", type=float); srl.set_defaults(func=cmd_swap_remove_liq)
    slp = ssw.add_parser("lp"); slp.add_argument("pool_id"); slp.add_argument("who")
    slp.set_defaults(func=cmd_swap_lp)
    ssw.add_parser("stats").set_defaults(func=cmd_swap_stats)

    # 🧬 poc
    ppoc = sub.add_parser("poc", help="🧬 Proof of Contribution (награды за вклад)")
    ppoc.add_argument("--node", default=DEFAULT_NODE)
    psub = ppoc.add_subparsers(dest="poc_cmd", required=True)

    psub.add_parser("categories", help="Категории вклада").set_defaults(func=cmd_poc_categories)

    psub.add_parser("pool", help="Состояние фонда").set_defaults(func=cmd_poc_pool)

    pd = psub.add_parser("donate", help="Пожертвовать в фонд")
    pd.add_argument("wallet"); pd.add_argument("amount", type=float)
    pd.set_defaults(func=cmd_poc_donate)

    psubm = psub.add_parser("submit", help="Создать вклад")
    psubm.add_argument("contributor", help="Имя кошелька-контрибьютора")
    psubm.add_argument("category", help="CODE / TRANSLATION / DOCS / BUG / DESIGN / PROMO / COMMUNITY / EDUCATION")
    psubm.add_argument("title", help="Краткое описание")
    psubm.add_argument("description", help="Подробности")
    psubm.add_argument("reward", type=float, help="Запрошенная награда в AIX")
    psubm.add_argument("--proof", "-p", default=None, help="URL доказательства (PR, ссылка)")
    psubm.set_defaults(func=cmd_poc_submit)

    pc2 = psub.add_parser("confirm", help="Подтвердить вклад")
    pc2.add_argument("contribution_id"); pc2.add_argument("reviewer")
    pc2.set_defaults(func=cmd_poc_confirm)

    pr = psub.add_parser("reject", help="Отклонить вклад")
    pr.add_argument("contribution_id"); pr.add_argument("reviewer")
    pr.add_argument("--reason", "-r", default="")
    pr.set_defaults(func=cmd_poc_reject)

    ppay = psub.add_parser("pay", help="Выплатить награду")
    ppay.add_argument("contribution_id"); ppay.set_defaults(func=cmd_poc_pay)

    pi = psub.add_parser("info", help="Инфо о вкладе")
    pi.add_argument("contribution_id"); pi.set_defaults(func=cmd_poc_info)

    pl = psub.add_parser("list", help="Вклады контрибьютора")
    pl.add_argument("who"); pl.set_defaults(func=cmd_poc_list)

    psub.add_parser("pending", help="Ожидают подтверждения").set_defaults(func=cmd_poc_pending)
    psub.add_parser("confirmed", help="Подтверждены, ждут выплаты").set_defaults(func=cmd_poc_confirmed)
    psub.add_parser("stats", help="Статистика").set_defaults(func=cmd_poc_stats)
    psub.add_parser("leaderboard", help="Топ контрибьюторов").set_defaults(func=cmd_poc_leaderboard)

        # 🧠 ai — AI Memory (#AI-1)
    pai = sub.add_parser("ai", help="🧠 AI Memory (#AI-1)")
    asub = pai.add_subparsers(dest="ai_cmd", required=True)

    ar = asub.add_parser("remember", help="Записать воспоминание")
    ar.add_argument("text")
    ar.add_argument("--kind", default="THOUGHT", choices=AI_KINDS)
    ar.add_argument("--priority", default="NORMAL", choices=AI_PRIORITIES)
    ar.add_argument("--tags", default="", help="через запятую: mempool,chain")
    ar.add_argument("--session", default=None)
    ar.add_argument("--chain-ref", dest="chain_ref", default="")
    ar.set_defaults(func=cmd_ai_remember)

    ab = asub.add_parser("brief", help="Собрать бриф")
    ab.add_argument("--output", "-o", default=None)
    ab.add_argument("--critical", type=int, default=10)
    ab.add_argument("--latest", type=int, default=20)
    ab.set_defaults(func=cmd_ai_brief)

    asub.add_parser("stats", help="Статистика").set_defaults(func=cmd_ai_stats)

    al = asub.add_parser("list", help="Список воспоминаний")
    al.add_argument("--kind", default=None, choices=AI_KINDS)
    al.add_argument("--tag", default=None)
    al.add_argument("--session", default=None)
    al.add_argument("--limit", "-n", type=int, default=20)
    al.set_defaults(func=cmd_ai_list)

    # DAO (#13)
    pdao = sub.add_parser("dao", help="DAO (#13)")
    pdao.add_argument("--node", default=DEFAULT_NODE)
    dsub = pdao.add_subparsers(dest="dao_cmd", required=True)

    dsub.add_parser("stats", help="Statistics").set_defaults(func=cmd_dao_stats)
    dsub.add_parser("list", help="All proposals").set_defaults(func=cmd_dao_list)

    dsh = dsub.add_parser("show", help="Show proposal")
    dsh.add_argument("proposal_id")
    dsh.set_defaults(func=cmd_dao_show)

    dcr = dsub.add_parser("create", help="Create proposal")
    dcr.add_argument("author", help="Wallet name")
    dcr.add_argument("title")
    dcr.add_argument("description")
    dcr.add_argument("--kind", default="TEXT", choices=["TEXT", "SPEND"])
    dcr.add_argument("--contribution", default=None,
                     help="For SPEND: contribution_id")
    dcr.set_defaults(func=cmd_dao_create)

    dv = dsub.add_parser("vote", help="Vote")
    dv.add_argument("proposal_id")
    dv.add_argument("voter", help="Wallet name")
    dv.add_argument("choice", choices=["yes", "no"])
    dv.set_defaults(func=cmd_dao_vote)

    dt = dsub.add_parser("tally", help="Finalize voting")
    dt.add_argument("proposal_id")
    dt.set_defaults(func=cmd_dao_tally)

    de = dsub.add_parser("execute", help="Execute passed proposal")
    de.add_argument("proposal_id")
    de.set_defaults(func=cmd_dao_execute)

    # BRAIN -- AI-напарник
    pbrain = sub.add_parser("brain", help="AIX Brain (локальная LLM)")
    pbrain.add_argument("--node", default=DEFAULT_NODE)
    pb_sub = pbrain.add_subparsers(dest="brain_cmd", required=True)

    pb_sub.add_parser("health", help="Проверить бэкенд и модель").set_defaults(
        func=cmd_brain_health)

    pba = pb_sub.add_parser("ask", help="Спросить AIX Brain")
    pba.add_argument("message")
    pba.add_argument("--model", default=None)
    pba.add_argument("--wallet", default=None,
                     help="Кошелёк для безопасной отправки (y/N)")
    pba.set_defaults(func=cmd_brain_ask)

    pbr = pb_sub.add_parser("remember", help="Записать в AI Memory")
    pbr.add_argument("title")
    pbr.add_argument("--kind", default="THOUGHT", choices=AI_KINDS)
    pbr.add_argument("--priority", default="NORMAL", choices=AI_PRIORITIES)
    pbr.add_argument("--body", default="")
    pbr.add_argument("--tags", default="")
    pbr.set_defaults(func=cmd_brain_remember)

    pbc = pb_sub.add_parser("chat", help="Интерактивный диалог")
    pbc.add_argument("--model", default=None)
    pbc.add_argument("--wallet", default=None,
                     help="Кошелёк для безопасной отправки (y/N)")
    pbc.set_defaults(func=cmd_brain_chat)

    pbs = pb_sub.add_parser("send", help="Отправить AIX (y/N + подпись)")
    pbs.add_argument("wallet", help="Имя кошелька-отправителя")
    pbs.add_argument("recipient", help="AIX-адрес, @id, имя или phone:+7...")
    pbs.add_argument("amount", type=float, help="Сумма в AIX")
    pbs.add_argument("--message", "-m", default="")
    pbs.set_defaults(func=cmd_brain_send)

    # FAUCET
    pf = sub.add_parser("faucet", help="AIX Faucet (кран)")
    pf.add_argument("--node", default=DEFAULT_NODE)
    fsub = pf.add_subparsers(dest="faucet_cmd", required=True)

    fsub.add_parser("stats", help="Статистика крана").set_defaults(
        func=cmd_faucet_stats)

    flog = fsub.add_parser("log", help="Журнал выдач")
    flog.add_argument("--limit", "-n", type=int, default=50)
    flog.set_defaults(func=cmd_faucet_log)

    fst = fsub.add_parser("set-treasury", help="Назначить кошелёк-казначей")
    fst.add_argument("wallet", help="Имя кошелька-казначея")
    fst.set_defaults(func=cmd_faucet_set_treasury)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    print(f"{Fore.MAGENTA}{config.ASCII_LOGO}")
    try: sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Прервано"); sys.exit(130)