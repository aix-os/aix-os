#!/usr/bin/env python3
"""AIX OS — Vesting Foundation Reserve (10% pre-mine, 4 года linear)."""
from pathlib import Path
import time
import json
import secrets
import os
import config

# 10% от 21 млрд
AIX_DEV_TOTAL_AIX = 2_100_000_000
AIX_DEV_TOTAL_RAW = AIX_DEV_TOTAL_AIX * config.SATOSHI
AIX_DEV_VESTING_START = 1764547200  # 1 декабря 2025 00:00 UTC
AIX_DEV_VESTING_DURATION = 4 * 365 * 86400  # 4 года

# Глобальные переменные (заполняются при первом импорте)
AIX_DEV_PRIVATE_KEY = None
AIX_DEV_PUBLIC_KEY = None
AIX_DEV_ADDRESS = None

KEY_FILE = Path("data/aix_dev_key.json")

def _load_or_create_key():
    global AIX_DEV_PRIVATE_KEY, AIX_DEV_PUBLIC_KEY, AIX_DEV_ADDRESS
    if KEY_FILE.exists():
        try:
            data = json.loads(KEY_FILE.read_text(encoding="utf-8"))
            AIX_DEV_PRIVATE_KEY = data["private_key"]
            AIX_DEV_PUBLIC_KEY = data["public_key"]
            AIX_DEV_ADDRESS = data["address"]
            return
        except Exception as e:
            print(f"[vesting] Ошибка чтения {KEY_FILE}: {e}")
    
    # Генерируем новый ключ
    try:
        from crypto.keys import private_key_from_bytes, get_public_key_bytes
        from crypto.address import private_key_to_address
    except Exception as e:
        print(f"[vesting] Не удалось импортировать crypto: {e}")
        return
    
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    priv_bytes = secrets.token_bytes(32)
    sk = private_key_from_bytes(priv_bytes)
    addr = private_key_to_address(sk)
    pub_hex = get_public_key_bytes(sk).hex()
    priv_hex = priv_bytes.hex()
    
    data = {
        "address": addr,
        "public_key": pub_hex,
        "private_key": priv_hex,
        "warning": "СЕКРЕТНО. Этот ключ даёт доступ к AIX-DEV кошельку с 2.1 млрд AIX. НИКОМУ не показывай.",
        "created_at": time.time(),
    }
    KEY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    
    AIX_DEV_PRIVATE_KEY = priv_hex
    AIX_DEV_PUBLIC_KEY = pub_hex
    AIX_DEV_ADDRESS = addr
    print(f"[vesting] 🆕 Создан AIX-DEV кошелёк: {addr}")
    print(f"[vesting] 🔐 Приватный ключ сохранён в {KEY_FILE}")

_load_or_create_key()

_blockchain = None

def init(blockchain):
    global _blockchain
    _blockchain = blockchain

def get_vesting_status():
    now = time.time()
    elapsed = max(0, now - AIX_DEV_VESTING_START)
    progress = min(1.0, elapsed / AIX_DEV_VESTING_DURATION)
    unlocked_raw = int(AIX_DEV_TOTAL_RAW * progress)
    
    already_sent_raw = 0
    if _blockchain is not None:
        for block in _blockchain.chain:
            for tx in block.transactions:
                if tx.sender == AIX_DEV_ADDRESS:
                    already_sent_raw += tx.amount + tx.fee
    
    available_raw = max(0, unlocked_raw - already_sent_raw)
    
    return {
        "address": AIX_DEV_ADDRESS,
        "total_aix": AIX_DEV_TOTAL_AIX,
        "unlocked_aix": unlocked_raw / config.SATOSHI,
        "already_sent_aix": already_sent_raw / config.SATOSHI,
        "available_aix": available_raw / config.SATOSHI,
        "available_raw": available_raw,
        "progress": round(progress, 6),
        "start_date": AIX_DEV_VESTING_START,
        "duration_seconds": AIX_DEV_VESTING_DURATION,
        "now": now,
    }

def can_send(amount, fee):
    s = get_vesting_status()
    return (amount + fee) <= s["available_raw"], s
