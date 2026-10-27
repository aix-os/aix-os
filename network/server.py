"""
AIX OS — REST API + P2P нода (Gift + TimeLock + SBT + Lottery + DMS + AIX-ID + Burn + Contacts + Swap + PoC + State Sync).
"""

import argparse
import asyncio
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import Request,  FastAPI, HTTPException
from fastapi import UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from core.chain import Blockchain
from core.block import Block
from core.transaction import Transaction
from core.transaction import calculate_fee
from core.wallet import Wallet
from core.protocols.gift_link import GiftLinkManager
from core.protocols.time_lock import TimeLockManager, parse_date, format_time
from core.protocols.sbt import SBTManager, MEDAL_CATALOG
from core.protocols.lottery import (
    is_lottery_block, pick_lottery_winner, compute_lottery_stats,
    LOTTERY_PRIZE, LOTTERY_CHANCE,
)
from core.protocols.dead_mans_switch import InheritanceManager, Heir
from core.protocols.aix_id import AIXIDManager, AIXProfile, validate_name
from core.protocols.burn_to_mint import BurnToMintManager, BURN_CATALOG
from core.protocols.contacts import (
    ContactsManager, Contact, phone_hash, normalize_phone, validate_phone,
)
from core.protocols.swap import (
    SwapManager, SwapPool, TOKEN_CATALOG, FAUCET_AMOUNT,
)
from core.protocols.poc import (
    PoCManager, Contribution, RewardPool, CATEGORIES,
    POC_POOL_ADDRESS, get_required_confirmations,
)
from core.protocols.state_sync import (
    export_state, import_state, apply_event,
    make_gift_event, make_timelock_event, make_medal_event,
    make_inheritance_event, make_id_event, make_burn_event, make_contact_event,
    make_swap_event, make_poc_event, make_poc_pool_event,
)
from core.protocols.ai_memory import (
    AIMemoryManager, KINDS as AI_KINDS, PRIORITIES as AI_PRIORITIES,
    KIND_EMOJI, PRIORITY_EMOJI,
)
from core.protocols.p2p import (
    P2PManager, P2POrder, SYSTEM_ESCROW_ADDRESS,
    PAYMENT_METHODS as P2P_PAYMENT_METHODS,
)

from storage.db import ChainStorage
from network.peer_manager import PeerManager
from network.ws_manager import ConnectionManager
from network.discovery import MdnsDiscovery
from core.protocols.messenger import MessengerManager
from core.protocols.token_registry import TokenRegistry
from core.protocols.fiat import FiatManager, AIX_PRICE_RUB
from network.discovery import MdnsDiscovery
from core.governance.dao import DAOManager
from core.protocols.faucet import FaucetManager, FAUCET_AMOUNT_AIX
from ai.brain import BrainAgent, BrainConfig


class SendRequest(BaseModel):
    sender: str
    recipient: str
    amount: int
    amount_aix: float | None = None
    fee: int = 0
    private_key: str
    message: str = ""

class MineRequest(BaseModel):
    miner_address: str
    broadcast: bool = True

class CreateWalletRequest(BaseModel):
    name: str

class ImportWalletRequest(BaseModel):
    name: str
    private_key: str

class AddPeerRequest(BaseModel):
    url: str

class RegisterPeerRequest(BaseModel):
    url: str

class SyncBlockRequest(BaseModel):
    block: dict
    from_peer: str = ""

class SyncStateEventRequest(BaseModel):
    event: dict
    from_peer: str = ""


class SubmitTxRequest(BaseModel):
    sender: str
    recipient: str
    amount: int
    timestamp: float
    fee: int = 0
    message: str = ""
    public_key: str
    signature: str

class GiftCreateRequest(BaseModel):
    sender: str
    amount_aix: float
    ttl_days: int = 30
    message: str = ""

class GiftClaimRequest(BaseModel):
    code: str
    recipient: str

class GiftCancelRequest(BaseModel):
    code: str
    sender: str

class TimeLockCreateRequest(BaseModel):
    owner: str
    amount_aix: float
    until: str
    recipient: str = ""
    message: str = ""

class TimeLockReleaseRequest(BaseModel):
    lock_id: str
    by: str

class TimeLockCancelRequest(BaseModel):
    lock_id: str
    by: str

class SBTAwardRequest(BaseModel):
    medal_id: str
    owner: str
    issuer: str
    reason: str = ""

class SBTRevokeRequest(BaseModel):
    medal_id: str
    owner: str
    reason: str = ""

class HeirSpec(BaseModel):
    address: str
    share_percent: float
    name: str = ""

class InheritanceCreateRequest(BaseModel):
    owner: str
    heirs: list[HeirSpec]
    timeout_days: int = 365
    note: str = ""

class InheritanceCheckinRequest(BaseModel):
    owner: str

class InheritanceTriggerRequest(BaseModel):
    by: str

class InheritanceCancelRequest(BaseModel):
    by: str

class IDRegisterRequest(BaseModel):
    address: str
    name: str
    display_name: str = ""
    avatar: str = ""
    bio: str = ""

class IDUpdateRequest(BaseModel):
    address: str
    display_name: str | None = None
    avatar: str | None = None
    bio: str | None = None

class BurnMintRequest(BaseModel):
    address: str
    level: str
    private_key: str = ""

class ContactRegisterRequest(BaseModel):
    address: str
    phone: str
    label: str = ""

class ContactUnregisterRequest(BaseModel):
    address: str
    phone: str

class ContactLookupRequest(BaseModel):
    phone: str

class SwapFaucetRequest(BaseModel):
    address: str
    token: str

class SwapCreatePoolRequest(BaseModel):
    creator: str
    token_x: str
    token_y: str
    amount_x_aix: float
    amount_y_aix: float

class SwapAddLiquidityRequest(BaseModel):
    pool_id: str
    address: str
    amount_a_aix: float
    amount_b_aix: float

class SwapRemoveLiquidityRequest(BaseModel):
    pool_id: str
    address: str
    lp_amount_aix: float

class SwapQuoteRequest(BaseModel):
    pool_id: str
    from_token: str
    amount_in_aix: float

class SwapExecuteRequest(BaseModel):
    pool_id: str
    address: str
    from_token: str
    amount_in_aix: float

class PoCDonateRequest(BaseModel):
    address: str
    amount_aix: float

class PoCSubmitRequest(BaseModel):
    contributor: str
    category: str
    title: str
    description: str
    requested_reward_aix: float
    proof_url: str = ""

class PoCConfirmRequest(BaseModel):
    contribution_id: str
    reviewer: str

class PoCRejectRequest(BaseModel):
    contribution_id: str
    reviewer: str
    reason: str = ""

class PoCPayRequest(BaseModel):
    contribution_id: str
class MessageSendRequest(BaseModel):
    sender: str
    recipient: str
    text: str = ""
    reply_to: str = ""
    forwarded_from: str = ""
    media_id: str = ""
    media_mime: str = ""
    media_size: int = 0

class MessageReadRequest(BaseModel):
    message_id: str
    reader: str

class MessageReactRequest(BaseModel):
    message_id: str
    emoji: str
    by: str

class MessageEditRequest(BaseModel):
    message_id: str
    new_text: str
    by: str

class MessageDeleteRequest(BaseModel):
    message_id: str
    by: str
    for_all: bool = False

class MessagePinRequest(BaseModel):
    message_id: str



class AIRememberRequest(BaseModel):
    text: str
    kind: str = "THOUGHT"
    priority: str = "NORMAL"
    tags: list[str] = []
    session: str = ""
    chain_ref: str = ""
class P2PCreateOrderRequest(BaseModel):
    seller: str
    amount_aix: float
    price_rub_per_aix: float
    min_amount_aix: float
    max_amount_aix: float
    payment_method: str = "card"
    escrow_tx_id: str


class P2PAcceptRequest(BaseModel):
    buyer: str
    deal_amount_aix: float


class P2PConfirmPaidRequest(BaseModel):
    buyer: str


class P2PReleaseRequest(BaseModel):
    seller: str


class P2PCancelRequest(BaseModel):
    seller: str


class P2PDisputeRequest(BaseModel):
    by: str
    reason: str = ""


class P2PChatRequest(BaseModel):
    from_address: str
    text: str



class DAOCreateRequest(BaseModel):
    author: str
    title: str
    description: str
    kind: str = "TEXT"
    payload: dict = {}


class DAOVoteRequest(BaseModel):
    voter: str
    choice: str  # yes | no


class DAOCancelRequest(BaseModel):
    by: str


class FaucetClaimRequest(BaseModel):
    address: str


class BrainAskRequest(BaseModel):
    message: str
    model: str | None = None


SYNC_INTERVAL = 5.0

async def background_sync(blockchain, storage, peer_manager, port):
    while True:
        try:
            await asyncio.sleep(SYNC_INTERVAL)
            await asyncio.to_thread(peer_manager.ping_all)
            best = peer_manager.best_peer()
            if best is None:
                continue
            their_work = best.total_work or (2 ** best.difficulty) * (best.height + 1)
            our_work = blockchain.total_work()
            if best.height <= blockchain.height() and their_work <= our_work:
                continue
            chain_data = await asyncio.to_thread(best.get_chain)
            if chain_data is None:
                continue
            try:
                new_chain = [Block.from_dict(b) for b in chain_data["chain"]]
            except Exception as e:
                print(f"WARN: [{port}] Ошибка разбора: {e}")
                continue
            old_height = blockchain.height()
            their_difficulty = chain_data.get("difficulty", blockchain.difficulty)
            ok, msg = blockchain.replace_chain(new_chain, their_difficulty)
            if ok:
                storage.save(blockchain)
                print(f"[{port}] Цепочка: {old_height} -> {blockchain.height()}. {msg}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"WARN: [{port}] Ошибка автосинхронизации: {e}")


def create_app(port: int, data_file: str, self_url: str,
               peers_file: str, gifts_file: str, timelocks_file: str,
               sbt_file: str, inheritance_file: str, id_file: str,
               burn_file: str, contacts_file: str, swap_file: str,
               poc_file: str, p2p_file: str) -> FastAPI:

    storage = ChainStorage(data_file)
    loaded = storage.load()
    if loaded is None:
        print(f"[{port}] Новая цепочка")
        blockchain = Blockchain()
        storage.save(blockchain)
    else:
        print(f"[{port}] Загружено: высота {loaded.height()}")
        blockchain = loaded

    peer_manager = PeerManager(self_url, storage_path=peers_file)
    mdns = MdnsDiscovery(port, peer_manager)
    mdns = MdnsDiscovery(port, peer_manager)
    gift_manager = GiftLinkManager(gifts_file, blockchain=blockchain)
    timelock_manager = TimeLockManager(timelocks_file, blockchain=blockchain)
    sbt_manager = SBTManager(sbt_file, blockchain=blockchain)
    inheritance_manager = InheritanceManager(inheritance_file, blockchain=blockchain)
    id_manager = AIXIDManager(id_file, blockchain=blockchain)
    burn_manager = BurnToMintManager(burn_file, blockchain=blockchain)
    contacts_manager = ContactsManager(contacts_file, blockchain=blockchain)
    swap_manager = SwapManager(swap_file, blockchain=blockchain)
    poc_manager = PoCManager(poc_file, blockchain=blockchain)
    ai_memory_path = Path(data_file).parent / "ai_memory.json"
    ai_memory = AIMemoryManager(ai_memory_path)
    messenger = MessengerManager(Path(data_file).parent / "messenger.json")
    token_registry = TokenRegistry(Path(data_file).parent / "token_registry.json")
    # ????-?????????? ???????????????? ??????? ? ???? ??? ??????
    for _t in token_registry.list_custom():
        swap_manager.add_token(_t.symbol, _t.name, _t.emoji)
    fiat_manager = FiatManager(Path(data_file).parent / f"fiat_{port}.json", blockchain)
    ws_manager = ConnectionManager()
    p2p_manager = P2PManager(p2p_file, blockchain=blockchain)


    dao_path = Path(data_file).parent / f"dao_{port}.json"
    dao_manager = DAOManager(dao_path, blockchain=blockchain, sbt_manager=sbt_manager, poc_manager=poc_manager)

    faucet_path = Path(data_file).parent / f"faucet_{port}.json"
    faucet_manager = FaucetManager(faucet_path, blockchain=blockchain)



    brain_config = BrainConfig.from_env()

    def total_locked(address: str) -> int:
        return (gift_manager.locked_balance(address)
                + timelock_manager.locked_balance(address))

    def resolve_who(who: str) -> str:
        addr = id_manager.resolve(who)
        if addr:
            return addr
        # fallback: имя кошелька -> адрес
        try:
            if Wallet.exists(who):
                return Wallet.load(who).address
        except Exception:
            pass
        return who

    async def _pull_state_from_peers(port: int) -> dict:
        total_added = {"gifts": 0, "timelocks": 0, "medals": 0,
                       "inheritances": 0, "aix_ids": 0, "burn_artifacts": 0,
                       "contacts": 0, "swap_pools": 0, "poc_contributions": 0}
        for peer in list(peer_manager.peers.values()):
            if not peer.is_alive:
                peer.ping()
            if not peer.is_alive:
                continue
            state_data = peer.get_state()
            if not state_data:
                continue
            try:
                stats = import_state(state_data, gift_manager,
                                     timelock_manager, sbt_manager,
                                     inheritance_manager, id_manager,
                                     burn_manager, contacts_manager,
                                     swap_manager, poc_manager, dao_manager)
                for k in total_added:
                    total_added[k] += stats["added"].get(k, 0)
            except Exception as e:
                print(f"WARN: [{port}] Ошибка импорта от {peer.url}: {e}")
        return {"added": total_added}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await mdns.start()
        task = asyncio.create_task(
            background_sync(blockchain, storage, peer_manager, port)
        )
        await asyncio.sleep(1.0)
        
        # Принудительная синхронизация блоков при старте
        try:
            peer_manager.ping_all()
            peer_manager.exchange_peers()
            for _peer in list(peer_manager.peers.values()):
                if not _peer.is_alive:
                    _peer.ping()
                if _peer.is_alive and _peer.height > blockchain.height():
                    _chain_data = _peer.get_chain()
                    if _chain_data:
                        from core.block import Block as _Block
                        _new_chain = [_Block.from_dict(b) for b in _chain_data["chain"]]
                        _ok, _msg = blockchain.replace_chain(_new_chain, _chain_data.get("difficulty", blockchain.difficulty))
                        if _ok:
                            storage.save(blockchain)
                            print(f"[{port}] ✅ Принудительный sync с {_peer.url}: {blockchain.height()} блоков")
                            break
        except Exception as _e:
            print(f"[{port}] WARN: принудительный sync не удался: {_e}")
        
        pulled = await _pull_state_from_peers(port)
        print(f"[{port}] Автосинхронизация запущена")
        print(f"[{port}] Gift: {len(gift_manager)}")
        print(f"[{port}] TimeLock: {len(timelock_manager)}")
        print(f"[{port}] SBT: {len(sbt_manager)}")
        print(f"[{port}] Inherit: {len(inheritance_manager)}")
        print(f"[{port}] AIX-ID: {len(id_manager)}")
        print(f"[{port}] Burn: {len(burn_manager)}")
        print(f"[{port}] Contacts: {len(contacts_manager)}")
        print(f"[{port}] Swap: {len(swap_manager.pools)} pools")
        print(f"[{port}] PoC: {len(poc_manager)} contributions, pool={poc_manager.pool.balance_aix():.2f} AIX")
        print(f"[{port}] AI Memory: {ai_memory.count()} записей")
        print(f"[{port}] DAO: {len(dao_manager)} proposals")
        if pulled.get("added"):
            a = pulled["added"]
            print(f"[{port}] State: +{a.get('gifts', 0)} gifts, "
                  f"+{a.get('timelocks', 0)} locks, "
                  f"+{a.get('medals', 0)} medals, "
                  f"+{a.get('inheritances', 0)} inheritances, "
                  f"+{a.get('aix_ids', 0)} ids, "
                  f"+{a.get('burn_artifacts', 0)} artifacts, "
                  f"+{a.get('contacts', 0)} contacts, "
                  f"+{a.get('swap_pools', 0)} swap_pools, "
                 f"+{a.get('dao_proposals', 0)} dao, "
                  f"+{a.get('poc_contributions', 0)} poc_contributions")
        yield

        # MINE-SPEED-OPTIMIZED: финальный save при shutdown —
        # чтобы не потерять блоки, что были в буфере.
        try:
            storage.save(blockchain)
            print(f"[{port}] Финальный save: высота {blockchain.height()}")
        except Exception as e:
            print(f"[{port}] WARN: финальный save упал: {e}")

        await mdns.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(
        title=f"{config.PROJECT_NAME} :{port}",
        description=config.PROJECT_TAGLINE,
        version=config.VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    def root():
        return f"""
        <html><head><title>{config.PROJECT_NAME} :{port}</title>
        <style>
            body {{ background:#0A0E27; color:#00F0FF; font-family:'Courier New',monospace;
                    padding:40px; text-align:center; }}
            pre {{ color:#8B00FF; font-size:11px; }}
            h1 {{ color:#FFD700; }}
            .stat {{ display:inline-block; margin:10px; padding:15px;
                     border:2px solid #00F0FF; border-radius:10px; }}
            .v {{ font-size:28px; color:#FFD700; }}
            a {{ color:#00F0FF; }}
        </style></head><body>
        <pre>{config.ASCII_LOGO}</pre>
        <h1>Node :{port}</h1>
        <div class="stat"><div>Height</div><div class="v">{blockchain.height()}</div></div>
        <div class="stat"><div>TXs</div><div class="v">{blockchain.total_transactions()}</div></div>
        <div class="stat"><div>Peers</div><div class="v">{len(peer_manager)}</div></div>
        <div class="stat"><div>IDs</div><div class="v">{len(id_manager)}</div></div>
        <div class="stat"><div>Contacts</div><div class="v">{len(contacts_manager)}</div></div>
        <div class="stat"><div>Swap pools</div><div class="v">{len(swap_manager.pools)}</div></div>
        <div class="stat"><div>PoC</div><div class="v">{len(poc_manager)}</div></div>
        <hr style="border-color:#8B00FF;">
        <p><a href="/docs">Swagger</a> | <a href="/peers">Peers</a></p>
        </body></html>
        """

    @app.get("/status")
    def status():
        return {
            "project": config.PROJECT_NAME, "version": config.VERSION,
            "coin": config.COIN_SYMBOL, "port": port, "self_url": self_url,
            "height": blockchain.height(), "difficulty": blockchain.difficulty,
            "total_work": blockchain.total_work(),
            "total_transactions": blockchain.total_transactions(),
            "mempool_size": blockchain.mempool.size(),
            "total_supply_aix": blockchain.total_supply() / config.SATOSHI,
            "total_burned_aix": blockchain.total_burned() / config.SATOSHI,
            "last_block_hash": blockchain.last_block().hash,
            "chain_valid": True,  # TODO: move to background task
            "peers_count": len(peer_manager),
            "gifts_count": len(gift_manager),
            "gifts_active": len(gift_manager.list_active()),
            "timelocks_count": len(timelock_manager),
            "timelocks_active": len(timelock_manager.list_active()),
            "sbt_count": len(sbt_manager),
            "inheritances_count": len(inheritance_manager),
            "inheritances_active": len(inheritance_manager.list_active()),
            "ids_count": len(id_manager),
            "burn_count": len(burn_manager),
            "contacts_count": len(contacts_manager),
            "contacts_addresses": contacts_manager.unique_addresses(),
            "swap_pools_count": len(swap_manager.pools),
            "poc_count": len(poc_manager),
            "poc_pool_aix": poc_manager.pool.balance_aix(),
            "ai_memory_count": ai_memory.count(),
            "dao_count": len(dao_manager),
        }

    @app.get("/chain")
    def get_chain(limit: int = 20):
        chain = blockchain.chain[-limit:] if limit else blockchain.chain
        return {"height": blockchain.height(), "returned": len(chain),
                "blocks": [b.to_dict() for b in chain]}

    @app.get("/blocks/{index}")
    def get_block(index: int):
        if index < 0 or index >= len(blockchain.chain):
            raise HTTPException(404, f"Блок #{index} не найден")
        return blockchain.chain[index].to_dict()

    @app.get("/balance/{address}")
    def get_balance(address: str):
        addr = resolve_who(address)
        bal = blockchain.get_balance(addr)
        gift_locked = gift_manager.locked_balance(addr)
        tl_locked = timelock_manager.locked_balance(addr)
        total_locked_val = gift_locked + tl_locked
        profile = id_manager.get_by_address(addr)
        return {
            "address": addr,
            "name": profile.name if profile else None,
            "avatar": profile.avatar if profile else None,
            "balance_raw": bal,
            "balance_aix": bal / config.SATOSHI,
            "locked_raw": total_locked_val,
            "locked_aix": total_locked_val / config.SATOSHI,
            "locked_breakdown": {
                "gift": gift_locked / config.SATOSHI,
                "timelock": tl_locked / config.SATOSHI,
            },
            "available_raw": bal - total_locked_val,
            "available_aix": (bal - total_locked_val) / config.SATOSHI,
            "reputation": sbt_manager.reputation(addr),
            "medals_count": len(sbt_manager.medals_of(addr)),
            "sim_balances": swap_manager.all_balances(addr),
        }

    @app.get("/mempool")
    def get_mempool():
        return {"size": blockchain.mempool.size(),
                "transactions": [tx.to_dict() for tx in blockchain.mempool.transactions.values()]}

    @app.post("/send")
    def send_transaction(req: SendRequest):
        sender_addr = resolve_who(req.sender)
        recipient_input = req.recipient
        recipient_addr = recipient_input

        if recipient_input.startswith("phone:"):
            phone = recipient_input[6:].strip()
            contact = contacts_manager.find_by_phone(phone)
            if contact is None:
                raise HTTPException(404, f"Номер {phone} не зарегистрирован в сети")
            recipient_addr = contact.address
        else:
            recipient_addr = resolve_who(recipient_input)

        amount = req.amount
        if req.amount_aix is not None:
            amount = int(req.amount_aix * config.SATOSHI)

        full_bal = blockchain.get_balance(sender_addr)
        locked = total_locked(sender_addr)
        available = full_bal - locked
        if available < amount + req.fee:
            raise HTTPException(400,
                f"Недостаточно свободных средств. Доступно: {available/config.SATOSHI:.2f} AIX")

        # AUTO-FEE-FIX: если клиент не передал комиссию — считаем сами (0.1%)
        effective_fee = req.fee if req.fee > 0 else calculate_fee(amount)
        tx = Transaction(sender=sender_addr, recipient=recipient_addr,
                         amount=amount, fee=effective_fee, message=req.message)
        try:
            from crypto.keys import private_key_from_bytes
            sk = private_key_from_bytes(bytes.fromhex(req.private_key))
            tx.sign_transaction(sk)
        except Exception as e:
            raise HTTPException(400, f"Ошибка подписи: {e}")

        ok, msg = tx.is_valid()
        if not ok:
            raise HTTPException(400, msg)
        ok, msg = blockchain.mempool.add(tx)
        if not ok:
            raise HTTPException(400, msg)

        storage.save(blockchain)
        broadcast_count = peer_manager.broadcast_transaction(tx.to_dict())

        return {"status": "accepted", "tx_id": tx.tx_id(),
                "recipient_resolved": recipient_addr,
                "broadcast_to_peers": broadcast_count,
                "mempool_size": blockchain.mempool.size()}

    @app.post("/mine")
    def mine(req: MineRequest):
        from crypto.address import is_valid_address
        miner_addr = resolve_who(req.miner_address)
        if not is_valid_address(miner_addr):
            raise HTTPException(400, "Невалидный адрес майнера")

        coinbase = Transaction.create_coinbase(
            recipient=miner_addr,
            amount=config.INITIAL_BLOCK_REWARD * config.SATOSHI)
        mempool_txs = blockchain.mempool.select_for_block(max_count=100)

        new_block = Block(index=blockchain.height() + 1, timestamp=time.time(),
                          transactions=[coinbase] + mempool_txs,
                          previous_hash=blockchain.last_block().hash)

        lottery_info = None
        if is_lottery_block(new_block):
            winner = pick_lottery_winner(blockchain, new_block)
            if winner:
                lottery_tx = Transaction.create_lottery(
                    recipient=winner,
                    amount=LOTTERY_PRIZE * config.SATOSHI,
                )
                new_block.transactions.append(lottery_tx)
                lottery_info = {"winner": winner, "prize_aix": LOTTERY_PRIZE}

        start = time.time()
        attempts = new_block.mine(difficulty=blockchain.difficulty)
        elapsed = time.time() - start

        ok, msg = blockchain.add_block(new_block)
        if not ok:
            raise HTTPException(500, f"Не удалось добавить блок: {msg}")

        # MINE-SPEED-OPTIMIZED: сохраняем не каждый блок, а раз в N
        save_every = getattr(config, "MINE_SAVE_EVERY_N_BLOCKS", 1)
        if save_every <= 1 or new_block.index % save_every == 0:
            storage.save(blockchain)

        # MINE-SPEED-OPTIMIZED: рассылка блока пирам — опционально
        broadcast_count = 0
        if req.broadcast and getattr(config, "MINE_BROADCAST", True):
            broadcast_count = peer_manager.broadcast_block(new_block.to_dict())

        result = {"status": "mined", "block_index": new_block.index,
                  "block_hash": new_block.hash, "nonce": new_block.nonce,
                  "attempts": attempts, "time_seconds": round(elapsed, 3),
                  "transactions_in_block": len(new_block.transactions),
                  "reward_aix": config.INITIAL_BLOCK_REWARD,
                  "miner": miner_addr,
                  "broadcast_to_peers": broadcast_count}
        if lottery_info:
            result["lottery"] = lottery_info
        return result

    @app.get("/wallets")
    def list_wallets():
        names = Wallet.list_wallets()
        result = []
        for name in names:
            try:
                w = Wallet.load(name)
                bal = blockchain.get_balance(w.address)
                locked = total_locked(w.address)
                profile = id_manager.get_by_address(w.address)
                result.append({
                    "name": name, "address": w.address,
                    "aix_id": profile.name if profile else None,
                    "avatar": profile.avatar if profile else None,
                    "balance_aix": bal / config.SATOSHI,
                    "locked_aix": locked / config.SATOSHI,
                    "available_aix": (bal - locked) / config.SATOSHI,
                    "reputation": sbt_manager.reputation(w.address),
                    "medals": len(sbt_manager.medals_of(w.address)),
                    "contacts": contacts_manager.count_for_address(w.address),
                })
            except Exception as e:
                result.append({"name": name, "error": str(e)})
        return {"count": len(result), "wallets": result}

    @app.post("/wallet/create")
    def create_wallet(req: CreateWalletRequest):
        if Wallet.exists(req.name):
            raise HTTPException(400, f"Кошелёк '{req.name}' уже существует")
        w = Wallet.create(req.name); w.save()
        return {"status": "created", "name": w.name, "address": w.address,
                "public_key": w.public_key}

    @app.post("/wallet/import")
    def import_wallet(req: ImportWalletRequest):
        if Wallet.exists(req.name):
            raise HTTPException(400, f"Кошелёк '{req.name}' уже существует")
        try:
            clean = req.private_key.strip().lower().replace("0x", "")
            priv_bytes = bytes.fromhex(clean)
            if len(priv_bytes) != 32:
                raise ValueError(f"Приватный ключ должен быть 32 байта (64 hex), получено {len(priv_bytes)}")
            from crypto.keys import private_key_from_bytes, get_public_key_bytes
            from crypto.address import private_key_to_address
            sk = private_key_from_bytes(priv_bytes)
            address = private_key_to_address(sk)
            pub = get_public_key_bytes(sk)
        except Exception as e:
            raise HTTPException(400, f"Невалидный приватный ключ: {e}")

        w = Wallet(
            name=req.name,
            address=address,
            public_key=pub.hex(),
            private_key=clean,
            created_at=time.time(),
        )
        w.save()
        return {"status": "imported", "name": w.name, "address": w.address,
                "public_key": w.public_key}

    # =========================================================================
    # GIFT
    # =========================================================================

    @app.post("/gift/create")
    def gift_create(req: GiftCreateRequest):
        from crypto.address import is_valid_address
        sender_addr = resolve_who(req.sender)
        if not is_valid_address(sender_addr):
            raise HTTPException(400, "Невалидный адрес отправителя")
        amount_raw = int(req.amount_aix * config.SATOSHI)
        try:
            link = gift_manager.create(sender=sender_addr, amount=amount_raw,
                                       ttl_days=req.ttl_days, message=req.message)
        except ValueError as e:
            raise HTTPException(400, str(e))

        event = make_gift_event(link)
        broadcast_count = peer_manager.broadcast_state_event(event)

        return {
            "status": "created", "code": link.code, "sender": link.sender,
            "amount_aix": link.amount / config.SATOSHI,
            "expires_in_days": req.ttl_days, "message": link.message,
            "share_url": f"{self_url}/gift/{link.code}",
            "broadcast_to_peers": broadcast_count,
        }

    @app.get("/gift/{code}")
    def gift_info(code: str):
        link = gift_manager.get(code)
        if link is None:
            raise HTTPException(404, "Gift-ссылка не найдена")
        return {"code": link.code, "sender": link.sender,
                "amount_aix": link.amount / config.SATOSHI,
                "status": link.status(), "created_at": link.created_at,
                "expires_at": link.expires_at, "message": link.message,
                "claimed": link.claimed, "claimed_by": link.claimed_by}

    @app.post("/gift/{code}/claim")
    def gift_claim(code: str, req: GiftClaimRequest):
        from crypto.address import is_valid_address
        recipient_addr = resolve_who(req.recipient)
        if not is_valid_address(recipient_addr):
            raise HTTPException(400, "Невалидный адрес получателя")
        ok, msg = gift_manager.claim(code, recipient_addr)
        if not ok:
            raise HTTPException(400, msg)

        link = gift_manager.get(code)
        if link:
            peer_manager.broadcast_state_event(make_gift_event(link))

        return {"status": "claimed", "code": code, "tx_id": msg,
                "recipient": recipient_addr}

    @app.post("/gift/{code}/cancel")
    def gift_cancel(code: str, req: GiftCancelRequest):
        sender_addr = resolve_who(req.sender)
        ok, msg = gift_manager.cancel(code, sender_addr)
        if not ok:
            raise HTTPException(400, msg)
        link = gift_manager.get(code)
        if link:
            peer_manager.broadcast_state_event(make_gift_event(link))
        return {"status": "cancelled", "code": code}

    @app.get("/gifts/sender/{address}")
    def gifts_by_sender(address: str):
        addr = resolve_who(address)
        links = gift_manager.list_by_sender(addr)
        return {"count": len(links), "links": [
            {"code": l.code, "amount_aix": l.amount / config.SATOSHI,
             "status": l.status(), "created_at": l.created_at,
             "expires_at": l.expires_at, "claimed_by": l.claimed_by}
            for l in links
        ]}

    # =========================================================================
    # TIMELOCK
    # =========================================================================

    @app.post("/timelock/create")
    def timelock_create(req: TimeLockCreateRequest):
        from crypto.address import is_valid_address
        owner_addr = resolve_who(req.owner)
        if not is_valid_address(owner_addr):
            raise HTTPException(400, "Невалидный адрес владельца")
        recipient_addr = resolve_who(req.recipient) if req.recipient else ""
        if recipient_addr and not is_valid_address(recipient_addr):
            raise HTTPException(400, "Невалидный адрес получателя")
        try:
            unlock_at = parse_date(req.until)
        except ValueError as e:
            raise HTTPException(400, str(e))
        amount_raw = int(req.amount_aix * config.SATOSHI)
        try:
            lock = timelock_manager.create(
                owner=owner_addr, amount=amount_raw,
                unlock_at=unlock_at, recipient=recipient_addr,
                message=req.message, blockchain=blockchain,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

        peer_manager.broadcast_state_event(make_timelock_event(lock))

        return {
            "status": "created", "id": lock.id, "owner": lock.owner,
            "recipient": lock.recipient or "(себе)",
            "amount_aix": lock.amount / config.SATOSHI,
            "unlock_at": format_time(lock.unlock_at),
            "unlock_at_ts": lock.unlock_at,
            "message": lock.message,
        }

    @app.get("/timelock/{lock_id}")
    def timelock_info(lock_id: str):
        lock = timelock_manager.get(lock_id)
        if lock is None:
            raise HTTPException(404, "Timelock не найден")
        return {
            "id": lock.id, "owner": lock.owner,
            "recipient": lock.recipient or "(себе)",
            "amount_aix": lock.amount / config.SATOSHI,
            "status": lock.status(),
            "created_at": lock.created_at,
            "unlock_at": lock.unlock_at,
            "unlock_at_str": format_time(lock.unlock_at),
            "time_left": lock.time_left_str(),
            "message": lock.message,
            "released": lock.released,
            "released_by": lock.released_by,
        }

    @app.post("/timelock/{lock_id}/release")
    def timelock_release(lock_id: str, req: TimeLockReleaseRequest):
        by_addr = resolve_who(req.by)
        ok, msg = timelock_manager.release(lock_id, by_addr, blockchain=blockchain)
        if not ok:
            raise HTTPException(400, msg)
        lock = timelock_manager.get(lock_id)
        if lock:
            peer_manager.broadcast_state_event(make_timelock_event(lock))
        return {"status": "released", "id": lock_id, "tx_id": msg}

    @app.post("/timelock/{lock_id}/cancel")
    def timelock_cancel(lock_id: str, req: TimeLockCancelRequest):
        by_addr = resolve_who(req.by)
        ok, msg = timelock_manager.cancel(lock_id, by_addr)
        if not ok:
            raise HTTPException(400, msg)
        lock = timelock_manager.get(lock_id)
        if lock:
            peer_manager.broadcast_state_event(make_timelock_event(lock))
        return {"status": "cancelled", "id": lock_id}

    @app.get("/timelocks/owner/{address}")
    def timelocks_by_owner(address: str):
        addr = resolve_who(address)
        locks = timelock_manager.list_by_owner(addr)
        return {"count": len(locks), "locks": [
            {"id": l.id, "owner": l.owner, "recipient": l.recipient or "(себе)",
             "amount_aix": l.amount / config.SATOSHI, "status": l.status(),
             "unlock_at": l.unlock_at, "unlock_at_str": format_time(l.unlock_at),
             "time_left": l.time_left_str(), "message": l.message}
            for l in locks
        ]}

    @app.get("/timelocks/recipient/{address}")
    def timelocks_by_recipient(address: str):
        addr = resolve_who(address)
        locks = timelock_manager.list_by_recipient(addr)
        return {"count": len(locks), "locks": [
            {"id": l.id, "owner": l.owner,
             "amount_aix": l.amount / config.SATOSHI, "status": l.status(),
             "unlock_at_str": format_time(l.unlock_at),
             "time_left": l.time_left_str()}
            for l in locks
        ]}

    # =========================================================================
    # SBT
    # =========================================================================

    @app.get("/sbt/catalog")
    def sbt_catalog():
        result = []
        for mid, info in MEDAL_CATALOG.items():
            issued = sbt_manager.count_by_medal_id(mid)
            result.append({
                "id": mid, "title": info["title"], "emoji": info["emoji"],
                "description": info["description"], "rarity": info["rarity"],
                "max_supply": info.get("max_supply"), "issued": issued,
            })
        return {"count": len(result), "medals": result}

    @app.post("/sbt/award")
    def sbt_award(req: SBTAwardRequest):
        from crypto.address import is_valid_address
        owner_addr = resolve_who(req.owner)
        issuer_addr = resolve_who(req.issuer)
        if not is_valid_address(owner_addr):
            raise HTTPException(400, "Невалидный адрес получателя")
        if not is_valid_address(issuer_addr):
            raise HTTPException(400, "Невалидный адрес выдающего")
        ok, msg, medal = sbt_manager.award(
            medal_id=req.medal_id.upper(),
            owner=owner_addr, issuer=issuer_addr, reason=req.reason,
        )
        if not ok:
            raise HTTPException(400, msg)
        broadcast_count = peer_manager.broadcast_state_event(make_medal_event(medal))
        return {
            "status": "awarded", "medal_id": medal.medal_id,
            "title": medal.title(), "emoji": medal.emoji(),
            "owner": medal.owner, "issuer": medal.issuer,
            "reason": medal.reason, "issued_at": medal.issued_at,
            "broadcast_to_peers": broadcast_count,
        }

    @app.post("/sbt/revoke")
    def sbt_revoke(req: SBTRevokeRequest):
        owner_addr = resolve_who(req.owner)
        ok, msg = sbt_manager.revoke(req.medal_id.upper(), owner_addr, req.reason)
        if not ok:
            raise HTTPException(400, msg)
        for m in sbt_manager.medals:
            if m.medal_id == req.medal_id.upper() and m.owner == owner_addr:
                peer_manager.broadcast_state_event(make_medal_event(m))
                break
        return {"status": "revoked", "medal_id": req.medal_id, "owner": owner_addr}

    @app.get("/sbt/owner/{address}")
    def sbt_by_owner(address: str):
        addr = resolve_who(address)
        medals = sbt_manager.medals_of(addr)
        return {
            "address": addr, "count": len(medals),
            "reputation": sbt_manager.reputation(addr),
            "medals": [
                {"id": m.medal_id, "title": m.title(), "emoji": m.emoji(),
                 "rarity": m.rarity(), "reason": m.reason,
                 "issuer": m.issuer, "issued_at": m.issued_at}
                for m in medals
            ],
        }

    @app.get("/sbt/leaderboard")
    def sbt_leaderboard(limit: int = 20):
        board = sbt_manager.leaderboard(limit=limit)
        enriched = []
        for addr, rep, cnt in board:
            profile = id_manager.get_by_address(addr)
            enriched.append({
                "address": addr,
                "name": profile.name if profile else None,
                "avatar": profile.avatar if profile else None,
                "reputation": rep,
                "medals": cnt,
            })
        return {"count": len(enriched), "top": enriched}

    # =========================================================================
    # LOTTERY
    # =========================================================================

    @app.get("/lottery/stats")
    def lottery_stats():
        return compute_lottery_stats(blockchain)

    @app.get("/lottery/info")
    def lottery_info():
        return {
            "chance": f"1/{LOTTERY_CHANCE}",
            "prize_aix": LOTTERY_PRIZE,
            "description": "Каждый блок имеет шанс 1/N стать счастливым.",
        }

    # =========================================================================
    # DMS
    # =========================================================================

    @app.post("/inherit/create")
    def inherit_create(req: InheritanceCreateRequest):
        from crypto.address import is_valid_address
        owner_addr = resolve_who(req.owner)
        if not is_valid_address(owner_addr):
            raise HTTPException(400, "Невалидный адрес владельца")
        heirs = []
        for h in req.heirs:
            h_addr = resolve_who(h.address)
            if not is_valid_address(h_addr):
                raise HTTPException(400, f"Невалидный адрес наследника: {h.address}")
            heirs.append(Heir(address=h_addr, share_percent=h.share_percent,
                              name=h.name))
        try:
            sw = inheritance_manager.create(
                owner=owner_addr, heirs=heirs,
                timeout_days=req.timeout_days, note=req.note,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        broadcast_count = peer_manager.broadcast_state_event(make_inheritance_event(sw))
        return {
            "status": "created", "id": sw.id, "owner": sw.owner,
            "heirs": [h.to_dict() for h in sw.heirs],
            "timeout_days": sw.timeout_days,
            "last_checkin": sw.last_checkin,
            "note": sw.note,
            "broadcast_to_peers": broadcast_count,
        }

    @app.get("/inherit/{sid}")
    def inherit_info(sid: str):
        sw = inheritance_manager.get(sid)
        if sw is None:
            raise HTTPException(404, "Switch не найден")
        return {
            "id": sw.id, "owner": sw.owner,
            "heirs": [h.to_dict() for h in sw.heirs],
            "timeout_days": sw.timeout_days,
            "created_at": sw.created_at,
            "last_checkin": sw.last_checkin,
            "status": sw.status(),
            "time_left": sw.time_left_str(),
            "note": sw.note,
            "triggered": sw.triggered,
            "triggered_by": sw.triggered_by,
            "cancelled": sw.cancelled,
        }

    @app.post("/inherit/{sid}/checkin")
    def inherit_checkin(sid: str, req: InheritanceCheckinRequest):
        owner_addr = resolve_who(req.owner)
        ok, msg, sw = inheritance_manager.check_in(owner_addr)
        if not ok:
            raise HTTPException(400, msg)
        if sw:
            peer_manager.broadcast_state_event(make_inheritance_event(sw))
        return {"status": "checked_in", "id": sw.id,
                "last_checkin": sw.last_checkin, "message": msg}

    @app.post("/inherit/{sid}/trigger")
    def inherit_trigger(sid: str, req: InheritanceTriggerRequest):
        sw = inheritance_manager.get(sid)
        if sw is None:
            raise HTTPException(404, "Switch не найден")
        by_addr = resolve_who(req.by)
        full_bal = blockchain.get_balance(sw.owner)
        locked = total_locked(sw.owner)
        available = max(0, full_bal - locked)
        ok, msg, tx_ids = inheritance_manager.trigger(
            sid, by_addr, blockchain=blockchain, available_balance=available,
        )
        if not ok:
            raise HTTPException(400, msg)
        sw = inheritance_manager.get(sid)
        if sw:
            peer_manager.broadcast_state_event(make_inheritance_event(sw))
        return {"status": "triggered", "id": sid, "tx_ids": tx_ids,
                "count": len(tx_ids), "message": msg,
                "available_aix": available / config.SATOSHI,
                "locked_aix": locked / config.SATOSHI}

    @app.post("/inherit/{sid}/cancel")
    def inherit_cancel(sid: str, req: InheritanceCancelRequest):
        by_addr = resolve_who(req.by)
        ok, msg = inheritance_manager.cancel(sid, by_addr)
        if not ok:
            raise HTTPException(400, msg)
        sw = inheritance_manager.get(sid)
        if sw:
            peer_manager.broadcast_state_event(make_inheritance_event(sw))
        return {"status": "cancelled", "id": sid}

    @app.get("/inherit/owner/{address}")
    def inherit_by_owner(address: str):
        addr = resolve_who(address)
        switches = inheritance_manager.list_by_owner(addr)
        return {"count": len(switches), "switches": [
            {"id": s.id, "owner": s.owner,
             "heirs": [h.to_dict() for h in s.heirs],
             "timeout_days": s.timeout_days,
             "status": s.status(), "time_left": s.time_left_str(),
             "last_checkin": s.last_checkin, "note": s.note}
            for s in switches
        ]}

    @app.get("/inherit/heir/{address}")
    def inherit_by_heir(address: str):
        addr = resolve_who(address)
        switches = inheritance_manager.list_by_heir(addr)
        return {"count": len(switches), "switches": [
            {"id": s.id, "owner": s.owner,
             "heirs": [h.to_dict() for h in s.heirs],
             "timeout_days": s.timeout_days,
             "status": s.status(), "time_left": s.time_left_str(),
             "note": s.note}
            for s in switches
        ]}

    # =========================================================================
    # AIX-ID
    # =========================================================================

    @app.post("/id/register")
    def id_register(req: IDRegisterRequest):
        owner_addr = resolve_who(req.address)
        ok, msg, profile = id_manager.register(
            address=owner_addr, name=req.name,
            display_name=req.display_name, avatar=req.avatar, bio=req.bio,
        )
        if not ok:
            raise HTTPException(400, msg)
        broadcast_count = peer_manager.broadcast_state_event(make_id_event(profile))
        return {
            "status": "registered", "name": profile.name,
            "address": profile.address, "display_name": profile.display_name,
            "avatar": profile.avatar, "bio": profile.bio,
            "created_at": profile.created_at,
            "broadcast_to_peers": broadcast_count,
        }

    @app.post("/id/update")
    def id_update(req: IDUpdateRequest):
        addr = resolve_who(req.address)
        ok, msg, profile = id_manager.update(
            address=addr, display_name=req.display_name,
            avatar=req.avatar, bio=req.bio,
        )
        if not ok:
            raise HTTPException(400, msg)
        broadcast_count = peer_manager.broadcast_state_event(make_id_event(profile))
        return {
            "status": "updated", "name": profile.name,
            "address": profile.address, "display_name": profile.display_name,
            "avatar": profile.avatar, "bio": profile.bio,
            "updated_at": profile.updated_at,
            "broadcast_to_peers": broadcast_count,
        }

    @app.get("/ids")
    def list_ids(limit: int = 50):
        profiles = id_manager.list_all(limit=limit)
        enriched = []
        for p in profiles:
            bal = blockchain.get_balance(p.address)
            enriched.append({
                "name": p.name, "address": p.address,
                "display_name": p.display_name, "avatar": p.avatar,
                "bio": p.bio, "balance_aix": bal / config.SATOSHI,
                "reputation": sbt_manager.reputation(p.address),
                "created_at": p.created_at,
            })
        return {"count": len(enriched), "profiles": enriched}

    @app.get("/id/resolve/{name}")
    def id_resolve(name: str):
        addr = id_manager.resolve(name)
        if addr is None:
            raise HTTPException(404, f"Имя '{name}' не найдено")
        return {"input": name, "address": addr}

    @app.get("/id/{name}")
    def id_info(name: str):
        profile = id_manager.get_by_name(name)
        if profile is None:
            profile = id_manager.get_by_address(name)
        if profile is None:
            raise HTTPException(404, "AIX-ID не найден")
        bal = blockchain.get_balance(profile.address)
        return {
            "name": profile.name, "address": profile.address,
            "display_name": profile.display_name, "avatar": profile.avatar,
            "bio": profile.bio, "created_at": profile.created_at,
            "updated_at": profile.updated_at, "verified": profile.verified,
            "balance_aix": bal / config.SATOSHI,
            "reputation": sbt_manager.reputation(profile.address),
            "medals_count": len(sbt_manager.medals_of(profile.address)),
        }

    # =========================================================================
    # BURN
    # =========================================================================

    @app.get("/burn/catalog")
    def burn_catalog():
        enriched = {}
        for level, info in BURN_CATALOG.items():
            enriched[level] = {
                **info,
                "issued": sum(1 for a in burn_manager.artifacts.values()
                              if a.level == level),
            }
        return {
            "catalog": enriched,
            "total_burned_aix": burn_manager.total_burned_aix(),
            "total_artifacts": len(burn_manager),
        }

    @app.post("/burn/mint")
    def burn_mint(req: BurnMintRequest):
        owner_addr = resolve_who(req.address)
        ok, msg, artifact = burn_manager.mint(
            owner=owner_addr, level=req.level, private_key=req.private_key, blockchain=blockchain,
        )
        if not ok:
            raise HTTPException(400, msg)
        broadcast_count = peer_manager.broadcast_state_event(make_burn_event(artifact))
        return {
            "status": "minted", "tx_id": msg,
            "artifact": artifact.to_dict(),
            "burned_aix": artifact.amount_burned / config.SATOSHI,
            "broadcast_to_peers": broadcast_count,
        }

    @app.get("/burn/stats")
    def burn_stats():
        return {
            "total_artifacts": len(burn_manager),
            "total_burned_aix": burn_manager.total_burned_aix(),
            "by_level": burn_manager.stats_by_level(),
        }

    @app.get("/burn/leaderboard")
    def burn_leaderboard(limit: int = 20):
        board = burn_manager.leaderboard(limit=limit)
        enriched = []
        for addr, total, rare, burned_aix in board:
            profile = id_manager.get_by_address(addr)
            enriched.append({
                "address": addr,
                "name": profile.name if profile else None,
                "avatar": profile.avatar if profile else None,
                "total": total, "rare": rare, "burned_aix": burned_aix,
            })
        return {"count": len(enriched), "top": enriched}

    @app.get("/burn/owner/{address}")
    def burn_by_owner(address: str):
        addr = resolve_who(address)
        artifacts = burn_manager.list_by_owner(addr)
        return {"address": addr, "count": len(artifacts),
                "artifacts": [a.to_dict() for a in artifacts]}

    @app.get("/burn/{artifact_id}")
    def burn_info(artifact_id: str):
        artifact = burn_manager.get(artifact_id)
        if artifact is None:
            raise HTTPException(404, "Артефакт не найден")
        return {
            "id": artifact.id, "level": artifact.level, "serial": artifact.serial,
            "owner": artifact.owner, "name": artifact.name, "emoji": artifact.emoji,
            "description": artifact.description, "rarity": artifact.rarity,
            "amount_burned": artifact.amount_burned,
            "amount_burned_aix": artifact.amount_burned / config.SATOSHI,
            "created_at": artifact.created_at, "burn_tx_id": artifact.burn_tx_id,
        }

    # =========================================================================
    # CONTACTS
    # =========================================================================

    @app.post("/contacts/register")
    def contacts_register(req: ContactRegisterRequest):
        from crypto.address import is_valid_address
        addr = resolve_who(req.address)
        if not is_valid_address(addr):
            raise HTTPException(400, "Невалидный адрес")
        ok, msg, contact = contacts_manager.register(
            address=addr, phone=req.phone, label=req.label,
        )
        if not ok:
            raise HTTPException(400, msg)
        broadcast_count = peer_manager.broadcast_state_event(make_contact_event(contact))
        return {
            "status": "registered", "phone_hash": contact.phone_hash,
            "address": contact.address, "label": contact.label,
            "broadcast_to_peers": broadcast_count,
        }

    @app.post("/contacts/unregister")
    def contacts_unregister(req: ContactUnregisterRequest):
        addr = resolve_who(req.address)
        ok, msg = contacts_manager.unregister(addr, req.phone)
        if not ok:
            raise HTTPException(400, msg)
        return {"status": "removed", "phone_hash": phone_hash(req.phone)}

    @app.post("/contacts/lookup")
    def contacts_lookup(req: ContactLookupRequest):
        ok, msg = validate_phone(req.phone)
        if not ok:
            raise HTTPException(400, msg)
        contact = contacts_manager.find_by_phone(req.phone)
        if contact is None:
            raise HTTPException(404, "Номер не зарегистрирован в сети")
        profile = id_manager.get_by_address(contact.address)
        return {
            "phone_hash": contact.phone_hash, "address": contact.address,
            "label": contact.label, "registered_at": contact.created_at,
            "aix_id": profile.name if profile else None,
            "display_name": profile.display_name if profile else None,
            "avatar": profile.avatar if profile else None,
        }

    @app.get("/contacts/stats")
    def contacts_stats():
        return {
            "total_contacts": len(contacts_manager),
            "unique_addresses": contacts_manager.unique_addresses(),
        }

    @app.get("/contacts/owner/{address}")
    def contacts_by_owner(address: str):
        addr = resolve_who(address)
        contacts = contacts_manager.find_by_address(addr)
        return {"address": addr, "count": len(contacts), "contacts": [
            {"phone_hash": c.phone_hash, "label": c.label,
             "created_at": c.created_at} for c in contacts
        ]}

    # =========================================================================
    # SWAP
    # =========================================================================

    @app.get("/swap/tokens")
    def swap_tokens():
        return {"tokens": TOKEN_CATALOG}

    @app.get("/swap/stats")
    def swap_stats():
        return swap_manager.stats()

    @app.get("/swap/balances/{address}")
    def swap_balances(address: str):
        addr = resolve_who(address)
        return {"address": addr, "balances": swap_manager.all_balances(addr)}


    @app.post("/swap/sync_balance")
    def swap_sync_balance(req: SwapFaucetRequest):
        """Синхронизирует реальный баланс AIX из блокчейна в Swap."""
        addr = resolve_who(req.address)
        # Получаем реальный баланс из блокчейна (в атомарных единицах)
        real_balance = blockchain.get_balance(addr)
        
        # Получаем текущий "виртуальный" баланс в Swap
        swap_balance = swap_manager.get_balance(addr, "AIX")
        
        # Если в блокчейне больше, чем в свапе, начисляем разницу
        if real_balance > swap_balance:
            diff = real_balance - swap_balance
            swap_manager.add_balance(addr, "AIX", diff)
            swap_manager._save()
            return {"status": "synced", "added": diff / config.SATOSHI}
        
        return {"status": "ok", "balance": swap_balance / config.SATOSHI}

    @app.post("/swap/faucet")
    def swap_faucet(req: SwapFaucetRequest):
        addr = resolve_who(req.address)
        ok, msg, amount = swap_manager.faucet(addr, req.token)
        if not ok:
            raise HTTPException(400, msg)
        return {"status": "ok", "address": addr, "token": req.token,
                "amount": amount, "amount_aix": amount / config.SATOSHI,
                "balance_after": swap_manager.get_balance(addr, req.token) / config.SATOSHI}

    @app.post("/swap/create_pool")
    def swap_create_pool(req: SwapCreatePoolRequest):
        creator_addr = resolve_who(req.creator)
        amount_x = int(req.amount_x_aix * config.SATOSHI)
        amount_y = int(req.amount_y_aix * config.SATOSHI)
        ok, msg, pool = swap_manager.create_pool(
            token_x=req.token_x, token_y=req.token_y,
            amount_x=amount_x, amount_y=amount_y,
            creator=creator_addr,
        )
        if not ok:
            raise HTTPException(400, msg)
        peer_manager.broadcast_state_event(make_swap_event(pool))
        return {
            "status": "created",
            "pool": {
                "id": pool.id, "token_a": pool.token_a, "token_b": pool.token_b,
                "reserve_a": pool.reserve_a / 10**18,
                "reserve_b": pool.reserve_b / 10**18,
                "price_a_in_b": pool.price_a_in_b(),
                "price_b_in_a": pool.price_b_in_a(),
                "total_lp": pool.total_lp / 10**18,
                "lp_holders": len(pool.lp_holders),
                "fee_percent": pool.fee_percent,
                "created_at": pool.created_at,
            },
            "message": msg,
        }

    @app.get("/swap/pools")
    def swap_list_pools():
        pools = swap_manager.list_pools()
        return {"count": len(pools), "pools": [
            {"id": p.id, "token_a": p.token_a, "token_b": p.token_b,
             "reserve_a": p.reserve_a / 10**18,
             "reserve_b": p.reserve_b / 10**18,
             "price_a_in_b": p.price_a_in_b(),
             "price_b_in_a": p.price_b_in_a(),
             "total_lp": p.total_lp / 10**18,
             "lp_holders": len(p.lp_holders),
             "fee_percent": p.fee_percent,
             "created_at": p.created_at}
            for p in pools
        ]}

    @app.get("/swap/pool/{pool_id:path}")
    def swap_pool_info(pool_id: str):
        pool = swap_manager.get_pool(pool_id)
        if pool is None:
            raise HTTPException(404, "Пул не найден")
        return {
            "id": pool.id, "token_a": pool.token_a, "token_b": pool.token_b,
            "reserve_a": pool.reserve_a / 10**18,
            "reserve_b": pool.reserve_b / 10**18,
            "price_a_in_b": pool.price_a_in_b(),
            "price_b_in_a": pool.price_b_in_a(),
            "total_lp": pool.total_lp / 10**18,
            "lp_holders_count": len(pool.lp_holders),
            "fee_percent": pool.fee_percent,
            "created_at": pool.created_at,
        }

    @app.post("/swap/add_liquidity")
    def swap_add_liquidity(req: SwapAddLiquidityRequest):
        addr = resolve_who(req.address)
        amount_a = int(req.amount_a_aix * config.SATOSHI)
        amount_b = int(req.amount_b_aix * config.SATOSHI)
        ok, msg, lp = swap_manager.add_liquidity(
            req.pool_id, addr, amount_a, amount_b,
        )
        if not ok:
            raise HTTPException(400, msg)
        pool = swap_manager.get_pool(req.pool_id)
        if pool:
            peer_manager.broadcast_state_event(make_swap_event(pool))
        return {"status": "ok", "pool_id": req.pool_id,
                "lp_tokens": lp, "lp_tokens_aix": lp / config.SATOSHI,
                "message": msg}

    @app.post("/swap/remove_liquidity")
    def swap_remove_liquidity(req: SwapRemoveLiquidityRequest):
        addr = resolve_who(req.address)
        lp_amount = int(req.lp_amount_aix * config.SATOSHI)
        ok, msg, amount_a, amount_b = swap_manager.remove_liquidity(
            req.pool_id, addr, lp_amount,
        )
        if not ok:
            raise HTTPException(400, msg)
        pool = swap_manager.get_pool(req.pool_id)
        if pool:
            peer_manager.broadcast_state_event(make_swap_event(pool))
        return {"status": "ok", "pool_id": req.pool_id,
                "amount_a": amount_a, "amount_a_aix": amount_a / config.SATOSHI,
                "amount_b": amount_b, "amount_b_aix": amount_b / config.SATOSHI}

    @app.get("/swap/lp/{pool_id:path}/{address}")
    def swap_lp_info(pool_id: str, address: str):
        addr = resolve_who(address)
        info = swap_manager.pool_lp_info(pool_id, addr)
        if not info:
            raise HTTPException(404, "Пул не найден")
        return info

    @app.post("/swap/quote")
    def swap_quote(req: SwapQuoteRequest):
        amount_in = int(req.amount_in_aix * 10**18)
        ok, msg, info = swap_manager.get_quote(req.pool_id, req.from_token, amount_in)
        if not ok:
            raise HTTPException(400, msg)
        return info

    @app.post("/swap/execute")
    def swap_execute(req: SwapExecuteRequest):
        addr = resolve_who(req.address)
        amount_in = int(req.amount_in_aix * 10**18)

        # Автосинк AIX: blockchain (8 dec) -> swap (18 dec)
        SWAP_DECIMALS = 10 ** 18
        real_aix = blockchain.get_balance(addr)
        real_aix_swap = int(real_aix * SWAP_DECIMALS / config.SATOSHI)
        swap_aix = swap_manager.get_balance(addr, "AIX")
        if real_aix_swap > swap_aix:
            swap_manager.add_balance(addr, "AIX", real_aix_swap - swap_aix)

        ok, msg, info = swap_manager.swap(
            req.pool_id, addr, req.from_token, amount_in
        )
        if not ok:
            raise HTTPException(400, msg)
        pool = swap_manager.get_pool(req.pool_id)
        if pool:
            peer_manager.broadcast_state_event(make_swap_event(pool))
        return info

    # =========================================================================
    # POC — ВАЖНО: специфичные эндпоинты ДО /poc/{id}
    # =========================================================================

    @app.get("/poc/categories")
    def poc_categories():
        return {"categories": CATEGORIES}

    @app.get("/poc/stats")
    def poc_stats():
        return poc_manager.stats()

    @app.get("/poc/pool")
    def poc_pool_info():
        return {
            "balance_aix": poc_manager.pool.balance_aix(),
            "total_donated_aix": poc_manager.pool.total_donated / config.SATOSHI,
            "total_paid_aix": poc_manager.pool.total_paid / config.SATOSHI,
            "donations_count": len(poc_manager.pool.donations),
            "payouts_count": len(poc_manager.pool.payouts),
        }

    @app.get("/poc/confirmed")
    def poc_confirmed():
        contributions = poc_manager.list_confirmed_unpaid()
        return {"count": len(contributions),
                "contributions": [c.to_dict() for c in contributions]}

    @app.get("/poc/pending")
    def poc_pending():
        contributions = poc_manager.list_by_status("pending")
        return {"count": len(contributions),
                "contributions": [c.to_dict() for c in contributions]}

    @app.get("/poc/all")
    def poc_all(limit: int = 50):
        contributions = poc_manager.list_all(limit=limit)
        return {"count": len(contributions),
                "contributions": [c.to_dict() for c in contributions]}

    @app.get("/poc/leaderboard")
    def poc_leaderboard(limit: int = 20):
        board = poc_manager.leaderboard(limit=limit)
        enriched = []
        for addr, count, reward_aix, paid in board:
            profile = id_manager.get_by_address(addr)
            enriched.append({
                "address": addr,
                "name": profile.name if profile else None,
                "avatar": profile.avatar if profile else None,
                "contributions": count,
                "reward_aix": reward_aix,
                "paid": paid,
            })
        return {"count": len(enriched), "top": enriched}

    @app.get("/poc/status/{status}")
    def poc_by_status(status: str):
        contributions = poc_manager.list_by_status(status)
        return {"count": len(contributions),
                "contributions": [c.to_dict() for c in contributions]}

    @app.get("/poc/contributor/{address}")
    def poc_by_contributor(address: str):
        addr = resolve_who(address)
        contributions = poc_manager.list_by_contributor(addr)
        return {"count": len(contributions),
                "contributions": [c.to_dict() for c in contributions]}

    # Динамический /poc/{id} — ОБЯЗАТЕЛЬНО в самом конце блока
    @app.get("/poc/{contribution_id}")
    def poc_info(contribution_id: str):
        c = poc_manager.get(contribution_id)
        if c is None:
            raise HTTPException(404, "Вклад не найден")
        return c.to_dict()

    @app.post("/poc/donate")
    def poc_donate(req: PoCDonateRequest):
        addr = resolve_who(req.address)
        amount = int(req.amount_aix * config.SATOSHI)
        ok, msg = poc_manager.donate(addr, amount, blockchain=blockchain)
        if not ok:
            raise HTTPException(400, msg)
        peer_manager.broadcast_state_event(make_poc_pool_event(poc_manager.pool))
        return {"status": "ok", "tx_id": msg,
                "pool_balance_aix": poc_manager.pool.balance_aix()}

    @app.post("/poc/submit")
    def poc_submit(req: PoCSubmitRequest):
        contributor_addr = resolve_who(req.contributor)
        reward = int(req.requested_reward_aix * config.SATOSHI)
        ok, result = poc_manager.submit(
            contributor=contributor_addr,
            category=req.category.upper(),
            title=req.title,
            description=req.description,
            requested_reward=reward,
            proof_url=req.proof_url,
        )
        if not ok:
            raise HTTPException(400, result)
        contribution_id = result
        c = poc_manager.get(contribution_id)
        peer_manager.broadcast_state_event(make_poc_event(c))
        return {
            "status": "created", "id": c.id,
            "contributor": c.contributor,
            "category": c.category,
            "title": c.title,
            "reward_aix": c.reward_aix(),
            "reward_level": c.reward_level,
            "required_confirmations": c.required_confirmations,
            "status_text": c.status,
        }

    @app.post("/poc/confirm")
    def poc_confirm(req: PoCConfirmRequest):
        reviewer_addr = resolve_who(req.reviewer)
        ok, msg = poc_manager.confirm(req.contribution_id, reviewer_addr)
        if not ok:
            raise HTTPException(400, msg)
        c = poc_manager.get(req.contribution_id)
        if c:
            peer_manager.broadcast_state_event(make_poc_event(c))
        return {
            "status": "ok",
            "contribution_id": req.contribution_id,
            "confirmations": c.confirmations_count() if c else 0,
            "required": c.required_confirmations if c else 0,
            "contribution_status": c.status if c else "?",
        }

    @app.post("/poc/reject")
    def poc_reject(req: PoCRejectRequest):
        reviewer_addr = resolve_who(req.reviewer)
        ok, msg = poc_manager.reject(req.contribution_id, reviewer_addr, req.reason)
        if not ok:
            raise HTTPException(400, msg)
        c = poc_manager.get(req.contribution_id)
        if c:
            peer_manager.broadcast_state_event(make_poc_event(c))
        return {"status": "ok", "contribution_id": req.contribution_id,
                "contribution_status": c.status if c else "?"}

    @app.post("/poc/pay")
    def poc_pay(req: PoCPayRequest):
        ok, msg = poc_manager.pay(req.contribution_id, blockchain=blockchain)
        if not ok:
            raise HTTPException(400, msg)
        c = poc_manager.get(req.contribution_id)
        if c:
            peer_manager.broadcast_state_event(make_poc_event(c))
        peer_manager.broadcast_state_event(make_poc_pool_event(poc_manager.pool))
        return {"status": "paid", "contribution_id": req.contribution_id,
                "tx_id": msg,
                "pool_balance_aix": poc_manager.pool.balance_aix()}

       # =========================================================================
    # AI MEMORY (#AI-1)
    # =========================================================================

    @app.get("/ai/memory")
    def ai_memory_brief(max_critical: int = 10, max_latest: int = 20):
        return {
            "count": ai_memory.count(),
            "sessions": ai_memory.sessions(),
            "brief": ai_memory.brief(max_critical=max_critical, max_latest=max_latest),
            "stats": ai_memory.stats(),
        }

    @app.get("/ai/memory/stats")
    def ai_memory_stats():
        return ai_memory.stats()

    @app.get("/ai/memory/latest")
    def ai_memory_latest(n: int = 20):
        return {"count": n, "memories": [m.to_dict() for m in ai_memory.latest(n)]}

    @app.get("/ai/memory/critical")
    def ai_memory_critical(n: int = 10):
        return {"count": n, "memories": [m.to_dict() for m in ai_memory.critical(n)]}

    @app.get("/ai/memory/session/{session}")
    def ai_memory_by_session(session: str):
        memories = [m for m in ai_memory.all() if m.session == session]
        return {"session": session, "count": len(memories),
                "memories": [m.to_dict() for m in memories]}

    @app.get("/ai/memory/tag/{tag}")
    def ai_memory_by_tag(tag: str):
        memories = ai_memory.by_tag(tag)
        return {"tag": tag, "count": len(memories),
                "memories": [m.to_dict() for m in memories]}

    @app.get("/ai/memory/kind/{kind}")
    def ai_memory_by_kind(kind: str):
        memories = ai_memory.by_kind(kind)
        return {"kind": kind.upper(), "count": len(memories),
                "memories": [m.to_dict() for m in memories]}

    @app.post("/ai/remember")
    def ai_remember(req: AIRememberRequest):
        try:
            mem = ai_memory.add(
                text=req.text, kind=req.kind, priority=req.priority,
                tags=req.tags, session=req.session or None,
                chain_ref=req.chain_ref,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {
            "status": "stored",
            "id": mem.hash[:12],
            "kind": mem.kind,
            "priority": mem.priority,
            "session": mem.session,
            "ts": mem.ts,
            "text": mem.text,
            "total": ai_memory.count(),
        }


    # =========================================================================
    # DAO (#13)
    # =========================================================================

    @app.get("/dao/stats")
    def dao_stats():
        return dao_manager.stats()

    @app.get("/dao/all")
    def dao_all(limit: int = 50):
        items = dao_manager.list_all(limit)
        return {"count": len(items), "proposals": [p.to_dict() for p in items]}

    @app.get("/dao/status/{status}")
    def dao_by_status(status: str):
        proposals = dao_manager.list_by_status(status)
        return {"status": status, "count": len(proposals),
                "proposals": [p.to_dict() for p in proposals]}

    @app.get("/dao/author/{address}")
    def dao_by_author(address: str):
        addr = resolve_who(address)
        proposals = dao_manager.list_by_author(addr)
        return {"author": addr, "count": len(proposals),
                "proposals": [p.to_dict() for p in proposals]}

    @app.get("/dao/{proposal_id}")
    def dao_info(proposal_id: str):
        p = dao_manager.get(proposal_id)
        if p is None:
            raise HTTPException(404, "Proposal not found")
        return p.to_dict()

    @app.post("/dao/create")
    def dao_create(req: DAOCreateRequest):
        author = resolve_who(req.author)
        ok, result = dao_manager.create_proposal(
            author=author,
            title=req.title,
            description=req.description,
            kind=req.kind,
            payload=req.payload,
        )
        if not ok:
            raise HTTPException(400, result)
        p = dao_manager.get(result)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "created", "id": p.id, "author": p.author,
                "kind": p.kind, "title": p.title,
                "voting_ends_at_height": p.voting_ends_at_height}

    @app.post("/dao/{proposal_id}/vote")
    def dao_vote(proposal_id: str, req: DAOVoteRequest):
        voter = resolve_who(req.voter)
        ok, msg = dao_manager.vote(proposal_id, voter, req.choice)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "voted", "id": proposal_id,
                "yes_weight": p.yes_weight(),
                "no_weight": p.no_weight(),
                "votes_count": p.votes_count(),
                "message": msg}

    @app.post("/dao/{proposal_id}/tally")
    def dao_tally(proposal_id: str):
        ok, msg = dao_manager.tally(proposal_id)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "tallied", "id": proposal_id,
                "proposal_status": p.status,
                "yes_weight": p.yes_weight(),
                "no_weight": p.no_weight()}

    @app.post("/dao/{proposal_id}/execute")
    def dao_execute(proposal_id: str):
        ok, msg = dao_manager.execute(proposal_id)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "executed", "id": proposal_id,
                "proposal_status": p.status,
                "tx_id": p.executed_tx_id,
                "message": msg}

    @app.post("/dao/{proposal_id}/cancel")
    def dao_cancel(proposal_id: str, req: DAOCancelRequest):
        by = resolve_who(req.by)
        ok, msg = dao_manager.cancel(proposal_id, by)
        if not ok:
            raise HTTPException(400, msg)
        p = dao_manager.get(proposal_id)
        peer_manager.broadcast_state_event({"kind": "dao_proposal", "data": p.to_dict()})
        return {"status": "cancelled", "id": proposal_id}

    # =========================================================================
    # BRAIN (AI-напарник)
    # =========================================================================

    @app.get("/brain/health")
    def brain_health():
        try:
            agent = BrainAgent(brain_config)
        except Exception as e:
            raise HTTPException(500, f"Brain недоступен: {e}")
        return agent.health()

    @app.post("/brain/ask")
    def brain_ask(req: BrainAskRequest):
        cfg = brain_config
        if req.model:
            cfg = cfg.with_model(req.model)
        try:
            agent = BrainAgent(cfg)
            answer = agent.ask(req.message)
        except Exception as e:
            raise HTTPException(500, f"Brain error: {e}")
        return {"status": "ok", "answer": answer, "model": cfg.model}

    # =========================================================================
    # FAUCET
    # =========================================================================

    @app.get("/faucet/stats")
    def faucet_stats():
        return faucet_manager.stats()

    @app.get("/faucet/log")
    def faucet_log(limit: int = 50):
        return {
            "count": faucet_manager.count(),
            "entries": faucet_manager.log(limit=limit),
        }

    @app.post("/faucet/claim")
    def faucet_claim(req: FaucetClaimRequest, request: Request):
        # Определяем IP
        ip = "?"
        if request.client and request.client.host:
            ip = request.client.host
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            ip = xff.split(",")[0].strip()

        try:
            ok, result, tx_id = faucet_manager.claim(address=req.address, ip=ip)
            if not ok:
                raise HTTPException(400, result)
            # 🔧 ФИКС: автоматом майним один блок, чтобы faucet-tx попал в блокчейн сразу
            # и баланс получателя обновился без ручного вызова /mine.
            try:
                mine_res = mine(MineRequest(miner_address=req.address, broadcast=True))
            except Exception:
                # Если майнинг не удался — tx остаётся в mempool, баланс придёт со следующим блоком
                pass
            return {
                "status": "sent",
                "address": req.address,
                "amount_aix": FAUCET_AMOUNT_AIX,
                "tx_id": tx_id,
                "treasury": "FAUCET (системный)",
            }
        except Exception as e:
            import traceback
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "type": type(e).__name__,
            }

    # =========================================================================
    # TRANSACTION SUBMIT (подписанная транзакция от кошелька)
    # =========================================================================

    @app.post("/tx/submit")
    def tx_submit(req: SubmitTxRequest):
        """
        Принять подписанную транзакцию от кошелька (мобильного/десктопного).
        Приватный ключ НЕ передаётся — только подпись и публичный ключ.
        """
        # AUTO-FEE-FIX: если fee=0 — считаем сами, но подпись уже сделана
        # на клиенте с fee=0. Поэтому отдаём правильный fee только если
        # клиент его не передал И может быть подписан с ним.
        # В нашем случае: подпись валидируется с фактическим fee, поэтому
        # если клиент подписал с fee=0, а мы подменим — подпись не сойдётся.
        # Значит для /tx/submit требуем, чтобы клиент сам передал fee.
        tx = Transaction(
            sender=req.sender,
            recipient=req.recipient,
            amount=req.amount,
            timestamp=req.timestamp,
            fee=req.fee,
            message=req.message,
            public_key=req.public_key,
            signature=req.signature,
        )

        ok, msg = tx.is_valid()
        if not ok:
            raise HTTPException(400, f"Транзакция невалидна: {msg}")

        # Проверка баланса для обычных отправителей
        if tx.sender not in ("COINBASE", "LOTTERY", "POC-POOL"):
            balance = blockchain.get_balance(tx.sender)
            locked = total_locked(tx.sender)
            available = balance - locked
            if available < tx.amount + tx.fee:
                raise HTTPException(
                    400,
                    f"Недостаточно средств: доступно "
                    f"{available / config.SATOSHI:.4f} AIX"
                )

        ok, msg = blockchain.mempool.add(tx)
        if not ok:
            raise HTTPException(400, msg)

        storage.save(blockchain)
        broadcast_count = peer_manager.broadcast_transaction(tx.to_dict())

        return {
            "status": "accepted",
            "tx_id": tx.tx_id(),
            "sender": tx.sender,
            "recipient": tx.recipient,
            "amount": tx.amount,
            "mempool_size": blockchain.mempool.size(),
            "broadcast_to_peers": broadcast_count,
        }

    # =========================================================================
    # CUSTOM-NETWORK: MetaMask / Trust Wallet
    # =========================================================================

    @app.get("/network/config")
    def network_config():
        """JSON для кнопки «Add Network» в MetaMask."""
        return {
            "chainId": hex(config.CHAIN_ID),
            "chainName": config.NETWORK_NAME,
            "nativeCurrency": {
                "name": config.NETWORK_SYMBOL,
                "symbol": config.NETWORK_SYMBOL,
                "decimals": config.NETWORK_DECIMALS,
            },
            "rpcUrls": [f"{self_url}/rpc"],
            "blockExplorerUrls": [],
        }

    @app.post("/rpc")
    def rpc_handler(req: dict):
        """
        Минимальный Ethereum JSON-RPC — для MetaMask/Trust.
        Поддерживает: eth_chainId, net_version, eth_blockNumber,
        eth_getBalance, eth_accounts, eth_gasPrice, eth_syncing,
        web3_clientVersion, eth_call (заглушка), eth_estimateGas.
        """
        method = req.get("method", "")
        params = req.get("params", [])
        req_id = req.get("id", 1)

        def _ok(result):
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        def _err(code, msg):
            return {"jsonrpc": "2.0", "id": req_id,
                    "error": {"code": code, "message": msg}}

        if method == "eth_chainId":
            return _ok(hex(config.CHAIN_ID))

        if method == "net_version":
            return _ok(str(config.CHAIN_ID))

        if method == "web3_clientVersion":
            return _ok(f"AIX-OS/v{config.VERSION}")

        if method == "eth_blockNumber":
            return _ok(hex(blockchain.height()))

        if method == "eth_syncing":
            return _ok(False)

        if method == "eth_gasPrice":
            return _ok("0x0")

        if method == "eth_accounts":
            return _ok([])

        if method == "eth_getBalance":
            try:
                addr = params[0] if params else ""
                # MetaMask отправляет 0x-адреса, но у нас AIX-адреса.
                # Возвращаем 0, если не можем сопоставить.
                bal = 0
                if addr and addr.startswith("AIX"):
                    bal = blockchain.get_balance(addr)
                return _ok(hex(bal))
            except Exception:
                return _ok("0x0")

        if method == "eth_call":
            # Заглушка — MetaMask вызывает для проверки контрактов
            return _ok("0x")

        if method == "eth_estimateGas":
            return _ok("0x5208")  # 21000 в hex

        # Всё остальное — ошибка method not found
        return _err(-32601, f"Method not found: {method}")



    # =========================================================================
    # TOKEN REGISTRY (??????? 2.0)
    # =========================================================================
    
    from pydantic import BaseModel
    class TokenRegisterRequest(BaseModel):
        creator: str
        symbol: str
        name: str
        total_supply: int
        emoji: str = "🪙"
        description: str = ""
        initial_pool_aix: float = 0.0
        initial_pool_token: float = 0.0
        usd_price: float = 0.0

    @app.post("/token/register")
    def token_register(req: TokenRegisterRequest):
        creator_addr = resolve_who(req.creator)

        # 0. Синхронизируем AIX из блокчейна в Swap (блокчейн = 8 dec, swap = 18 dec)
        SWAP_DECIMALS = 10 ** 18
        real_aix = blockchain.get_balance(creator_addr)  # 8 dec
        real_aix_swap = int(real_aix * SWAP_DECIMALS / config.SATOSHI)  # 18 dec
        swap_aix = swap_manager.get_balance(creator_addr, "AIX")  # 18 dec
        if real_aix_swap > swap_aix:
            swap_manager.add_balance(creator_addr, "AIX", real_aix_swap - swap_aix)

        # 1. Проверка реальной ликвидности AIX (в человеческих единицах)
        available_aix = swap_manager.get_balance(creator_addr, "AIX") / SWAP_DECIMALS
        if available_aix < req.initial_pool_aix:
            raise HTTPException(400,
                f"Недостаточно AIX в Swap: нужно {req.initial_pool_aix}, "
                f"есть {available_aix:.4f}")

        # --- Цена токена через oracle ---
        from core.oracle import get_usd_price, AIX_USD
        sym = req.symbol.upper()
        usd_price = float(req.usd_price) if req.usd_price > 0 else (get_usd_price(sym) or 0.0)
        if usd_price <= 0:
            raise HTTPException(400,
                f"Не знаю USD-цену для '{sym}'. Укажи её вручную (поле usd_price).")

        # --- Авто-расчёт второй стороны ликвидности ---
        aix_usd = float(AIX_USD)
        pool_aix = float(req.initial_pool_aix)
        pool_tok = float(req.initial_pool_token)
        if pool_aix > 0 and pool_tok <= 0:
            pool_tok = pool_aix * aix_usd / usd_price
        elif pool_tok > 0 and pool_aix <= 0:
            pool_aix = pool_tok * usd_price / aix_usd
        elif pool_aix > 0 and pool_tok > 0:
            # Проверим пропорцию: если расхождение > 5% — поправим
            expected_tok = pool_aix * aix_usd / usd_price
            if abs(pool_tok - expected_tok) / expected_tok > 0.05:
                pool_tok = expected_tok
        if pool_aix <= 0 or pool_tok <= 0:
            raise HTTPException(400,
                "Нужна реальная ликвидность (AIX > 0 или TOKEN > 0)")

        # Проверка баланса AIX после пересчёта
        if available_aix < pool_aix:
            raise HTTPException(400,
                f"Недостаточно AIX в Swap: нужно {pool_aix:.4f}, есть {available_aix:.4f}")

        # 2. Регистрация токена (swap = 18 dec)
        total_supply_raw = int(req.total_supply * SWAP_DECIMALS)
        initial_pool_aix_raw = int(pool_aix * SWAP_DECIMALS)
        initial_pool_token_raw = int(pool_tok * SWAP_DECIMALS)

        ok, msg = token_registry.register(
            creator=creator_addr,
            symbol=req.symbol,
            name=req.name,
            total_supply=total_supply_raw,
            emoji=req.emoji,
            description=req.description,
            initial_pool_aix=initial_pool_aix_raw,
            initial_pool_token=initial_pool_token_raw,
            usd_price=usd_price,
        )
        if not ok:
            raise HTTPException(400, msg)

        record = token_registry.get(req.symbol)
        swap_manager.add_token(req.symbol.upper(), req.name, req.emoji)

        # 3. Начисляем создателю эмиссию токенов в Swap
        swap_manager.add_balance(creator_addr, req.symbol.upper(), total_supply_raw)

        # 4. Создаём пул TOKEN/AIX
        ok_pool, pool_msg, pool = swap_manager.create_pool(
            token_x=req.symbol.upper(),
            token_y="AIX",
            amount_x=initial_pool_token_raw,
            amount_y=initial_pool_aix_raw,
            creator=creator_addr,
        )
        if not ok_pool:
            raise HTTPException(400, f"Токен зарегистрирован, но пул не создан: {pool_msg}")

        return {
            "status": "ok",
            "token": record.to_dict(),
            "pool": pool.to_dict(),
            "message": msg,
        }

    @app.get("/token/list")
    def token_list():
        tokens = token_registry.list_all()
        return {"count": len(tokens), "tokens": [t.to_dict() for t in tokens]}

    @app.get("/oracle/price/{symbol}")
    def oracle_price(symbol: str):
        """USD-цена для фронта. Если неизвестно — null."""
        from core.oracle import get_usd_price, AIX_USD
        p = get_usd_price(symbol)
        return {"symbol": symbol.upper(), "usd_price": p, "aix_usd": AIX_USD}

    @app.get("/oracle/known")
    def oracle_known():
        """Список тикеров, для которых есть live-цена."""
        from core.oracle import known_symbols
        return {"count": len(known_symbols()), "symbols": known_symbols()}

    @app.get("/token/{symbol}")
    def token_info(symbol: str):
        record = token_registry.get(symbol)
        if not record:
            raise HTTPException(404, f"Token {symbol} not found")
        return record.to_dict()

    @app.get("/messages/online")
    def messages_online():
        return {"online": ws_manager.online_list()}




    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"{config.PROJECT_NAME} — нода")
    parser.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    parser.add_argument("--host", default=config.DEFAULT_HOST)
    parser.add_argument("--data", default=str(config.CHAIN_DB_PATH))
    parser.add_argument("--peers", default=None)
    parser.add_argument("--gifts", default=None)
    parser.add_argument("--timelocks", default=None)
    parser.add_argument("--sbt", default=None)
    parser.add_argument("--inherit", dest="inheritance", default=None)
    parser.add_argument("--ids", dest="ids", default=None)
    parser.add_argument("--burn", dest="burn", default=None)
    parser.add_argument("--contacts", dest="contacts", default=None)
    parser.add_argument("--swap", dest="swap", default=None)
    parser.add_argument("--poc", dest="poc", default=None)
    parser.add_argument("--p2p", default=None)
    parser.add_argument("--url", default=None)
    args = parser.parse_args()

    self_url = args.url or f"http://localhost:{args.port}"
    data_dir = Path(args.data).parent
    peers_file = args.peers or str(data_dir / f"peers_{args.port}.json")
    gifts_file = args.gifts or str(data_dir / f"gifts_{args.port}.json")
    timelocks_file = args.timelocks or str(data_dir / f"timelocks_{args.port}.json")
    sbt_file = args.sbt or str(data_dir / f"sbt_{args.port}.json")
    inheritance_file = args.inheritance or str(data_dir / f"inheritance_{args.port}.json")
    ids_file = args.ids or str(data_dir / f"ids_{args.port}.json")
    burn_file = args.burn or str(data_dir / f"burn_{args.port}.json")
    contacts_file = args.contacts or str(data_dir / f"contacts_{args.port}.json")
    swap_file = args.swap or str(data_dir / f"swap_{args.port}.json")
    poc_file = args.poc or str(data_dir / f"poc_{args.port}.json")
    p2p_file = args.p2p or str(data_dir / f"p2p_{args.port}.json")

    app = create_app(args.port, args.data, self_url,
                     peers_file, gifts_file, timelocks_file, sbt_file,
                     inheritance_file, ids_file, burn_file, contacts_file,
                     swap_file, poc_file, p2p_file)

    import uvicorn
    print(config.ASCII_LOGO)
    print(f"AIX OS node v{config.VERSION}")
    print(f"URL:      {self_url}")
    print(f"Chain:    {args.data}")
    print(f"Gift:     {gifts_file}")
    print(f"Lock:     {timelocks_file}")
    print(f"SBT:      {sbt_file}")
    print(f"Inherit:  {inheritance_file}")
    print(f"IDs:      {ids_file}")
    print(f"Burn:     {burn_file}")
    print(f"Contacts: {contacts_file}")
    print(f"Swap:     {swap_file}")
    print(f"PoC:      {poc_file}")
    print(f"P2P:      {p2p_file}")
    print(f"Swagger:  {self_url}/docs")
    print()

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")