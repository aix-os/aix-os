# -*- coding: utf-8 -*-
"""AIX OS — Oracle цен (Империя 2.0).

Поддерживает ~120 популярных тикеров (ERC-20 / BEP-20 / SPL / TRC-20)
+ AIX (фикс. $100) + любые aCOIN.

Если тикер неизвестен oracle — используется ручная USD-цена от пользователя
при регистрации токена.
"""
from __future__ import annotations

import json
import time
import urllib.request
from threading import Lock
from typing import Optional

AIX_USD = 100.0

# ~120 популярных тикеров. Расширяемо.
COINGECKO_IDS = {
    # Топ капитализации
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "USDT":  "tether",
    "BNB":   "binancecoin",
    "SOL":   "solana",
    "USDC":  "usd-coin",
    "XRP":   "ripple",
    "STETH": "staked-ether",
    "DOGE":  "dogecoin",
    "ADA":   "cardano",
    "TRX":   "tron",
    "AVAX":  "avalanche-2",
    "TON":   "the-open-network",
    "SHIB":  "shiba-inu",
    "LINK":  "chainlink",
    "DOT":   "polkadot",
    "BCH":   "bitcoin-cash",
    "NEAR":  "near",
    "MATIC": "matic-network",
    "POL":   "polygon-ecosystem-token",
    "LTC":   "litecoin",
    "ICP":   "internet-computer",
    "UNI":   "uniswap",
    "DAI":   "dai",
    "APT":   "aptos",
    "LEO":   "leo-token",
    "XLM":   "stellar",
    "ETC":   "ethereum-classic",
    "ATOM":  "cosmos",
    "OKB":   "okb",
    "FIL":   "filecoin",
    "XMR":   "monero",
    "IMX":   "immutable-x",
    "HBAR":  "hedera-hashgraph",
    "ARB":   "arbitrum",
    "OP":    "optimism",
    "INJ":   "injective-protocol",
    "VET":   "vechain",
    "SUI":   "sui",
    "MNT":   "mantle",
    "RNDR":  "render-token",
    "GRT":   "the-graph",
    "MKR":   "maker",
    "AAVE":  "aave",
    "LDO":   "lido-dao",
    "RUNE":  "thorchain",
    "THETA": "theta-token",
    "FTM":   "fantom",
    "FET":   "fetch-ai",
    "TIA":   "celestia",
    "SEI":   "sei-network",
    "SAND":  "the-sandbox",
    "MANA":  "decentraland",
    "EOS":   "eos",
    "AXS":   "axie-infinity",
    "FLOW":  "flow",
    "EGLD":  "elrond-erd-2",
    "XTZ":   "tezos",
    "CHZ":   "chiliz",
    "GALA":  "gala",
    "COMP":  "compound-governance-token",
    "SNX":   "havven",
    "CRV":   "curve-dao-token",
    "KAVA":  "kava",
    "1INCH": "1inch",
    "SUSHI": "sushi",
    "YFI":   "yearn-finance",
    "BAL":   "balancer",
    "LRC":   "loopring",
    "ZEC":   "zcash",
    "DASH":  "dash",
    "XDC":   "xdce-crowd-sale",
    "KCS":   "kucoin-shares",
    "CRO":   "crypto-com-chain",
    "ROSE":  "oasis-network",
    "CELO":  "celo",
    "AR":    "arweave",
    "WAVES": "waves",
    "KSM":   "kusama",
    "ONE":   "harmony",
    "ZIL":   "zilliqa",
    "ENS":   "ethereum-name-service",
    "PEOPLE":"constitutiondao",
    "MASK":  "mask-network",
    "DYDX":  "dydx-chain",
    "GMT":   "stepn",
    "APE":   "apecoin",
    "CAKE":  "pancakeswap-token",
    "JUP":   "jupiter-exchange-solana",
    "PYTH":  "pyth-network",
    "BONK":  "bonk",
    "WIF":   "dogwifcoin",
    "BOME":  "book-of-meme",
    "JTO":   "jito-governance-token",
    "WLD":   "worldcoin-wld",
    "BLUR":  "blur",
    "AGIX":  "singularitynet",
    "OCEAN": "ocean-protocol",
    "AKT":   "akash-network",
    "KAS":   "kaspa",
    "STX":   "blockstack",
    "ORDI":  "ordinals",
    "BGB":   "bitget-token",
    "GT":    "gatechain-token",
    "HT":    "huobi-token",
    "WBT":   "whitebit",
    "NEXO":  "nexo",
    "XAUT":  "tether-gold",
    "PAXG":  "pax-gold",
    "USDD":  "usdd",
    "TUSD":  "true-usd",
    "FDUSD": "first-digital-usd",
    "USDP":  "paxos-standard",
    "GUSD":  "gemini-dollar",
    "FRAX":  "frax",
    "LUSD":  "liquity-usd",
    "MIM":   "magic-internet-money",
    "ALGO":  "algorand",
    "QNT":   "quant-network",
    "BSV":   "bitcoin-cash-sv",
    "MINA":  "mina-protocol",
    "AXL":   "axelar",
    "WOO":   "woo-network",
    # Доп. популярные (в кошельках)
    "PEPE":  "pepe",
    "FLOKI": "floki",
    "MOG":   "mog-coin",
    "TURBO": "turbo",
    "LADYS": "milady-meme-coin",
    "AIDOGE":"aidoge",
    "MEME":  "memecoin-2",
    "BRETT": "based-brett",
    "POPCAT":"popcat",
    "NEIRO": "neiro-3",
    "NOT":   "notcoin",
    "DOGS":  "dogs-2",
    "HMSTR": "hamster-kombat",
    "TON":   "the-open-network",
    "OKB":   "okb",
    "BGB":   "bitget-token",
    "GT":    "gatechain-token",
    "HT":    "huobi-token",
    "LEO":   "leo-token",
    "CRO":   "crypto-com-chain",
    "KCS":   "kucoin-shares",
    "FTT":   "ftx-token",
    "SRM":   "serum",
    "RAY":   "raydium",
    "ORCA":  "orca-so",
    "JTO":   "jito-governance-token",
    "PYTH":  "pyth-network",
    "TNSR":  "tensor",
    "DRIFT": "drift-protocol",
    "KMNO":  "kamino",
    "MEW":   "cat-in-a-dogs-world",
    "SLERF": "slerf",
    "BOME":  "book-of-meme",
    "WIF":   "dogwifcoin",
    "BONK":  "bonk",
    "MYRO":  "myro",
    "SAMO":  "samoyedcoin",
    "TREMP": "doland-tremp",
    "BODEN": "joeboden",
    "MOTHER":"mother-iggy",
    "ZEN":   "zencash",
}

FALLBACK_USD = {
    "AIX":  100.0,
    "BTC":  60000.0, "ETH": 3000.0, "USDT": 1.0, "USDC": 1.0,
    "BNB": 600.0, "SOL": 150.0, "XRP": 0.6, "DOGE": 0.15,
    "ADA": 0.5, "TON": 5.0, "TRX": 0.15, "LINK": 15.0,
    "MATIC": 0.6, "AVAX": 30.0, "DOT": 7.0, "SHIB": 0.000025,
    "LTC": 80.0, "BCH": 400.0, "UNI": 8.0, "DAI": 1.0,
    "ATOM": 8.0, "XLM": 0.12, "FIL": 5.0, "APT": 8.0,
    "ARB": 1.0, "OP": 2.0, "INJ": 25.0, "VET": 0.03,
    "SUI": 1.5, "NEAR": 5.0, "ETC": 25.0, "XMR": 150.0,
}

CACHE_TTL = 300.0
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"

_cache: dict[str, float] = {}
_cache_ts: float = 0.0
_lock = Lock()


def _fetch_live() -> dict[str, float]:
    ids = ",".join(sorted(set(COINGECKO_IDS.values())))
    req = urllib.request.Request(COINGECKO_URL.format(ids=ids),
                                 headers={"User-Agent": "AIX-OS/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        raw = json.load(r)
    out: dict[str, float] = {}
    for ticker, cg_id in COINGECKO_IDS.items():
        try:
            out[ticker] = float(raw[cg_id]["usd"])
        except (KeyError, TypeError, ValueError):
            pass
    return out


def refresh_prices(force: bool = False) -> dict[str, float]:
    global _cache, _cache_ts
    with _lock:
        now = time.time()
        if not force and _cache and (now - _cache_ts) < CACHE_TTL:
            return dict(_cache)
        try:
            live = _fetch_live()
            merged = dict(FALLBACK_USD)
            merged.update(live)
            merged["AIX"] = AIX_USD
            _cache = merged
            _cache_ts = now
        except Exception as e:
            print(f"WARN: oracle refresh failed: {e}")
            if not _cache:
                _cache = dict(FALLBACK_USD)
                _cache["AIX"] = AIX_USD
                _cache_ts = now
        return dict(_cache)


def get_usd_price(symbol: str) -> Optional[float]:
    sym = symbol.upper().strip()
    if sym == "AIX":
        return AIX_USD
    prices = refresh_prices()
    return prices.get(sym)


def known_symbols() -> list[str]:
    """Список тикеров, для которых есть автоподгрузка цены."""
    return sorted(COINGECKO_IDS.keys())
