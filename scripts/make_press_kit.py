"""Генерация документов для выхода AIX в мир (Листинг и DEX)."""
from pathlib import Path

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs" / "listing"
DOCS.mkdir(parents=True, exist_ok=True)

# =============================================================================
# 1. PRESS_KIT.md
# =============================================================================
press_kit = """# 📊 AIX OS — Press Kit (Данные для листинга)

## Основная информация
*   **Project Name:** AIX OS
*   **Ticker Symbol:** AIX
*   **Max Supply:** 21,000,000,000 AIX
*   **Decimals:** 8
*   **Consensus:** Proof of Work (PoW)
*   **Pre-mine:** 0%
*   **Launch Date:** 2026

## Краткое описание (Short Description)
> AIX OS is a decentralized operating system for life. It features a native blockchain with Proof of Work, an integrated Local LLM AI assistant (AIX Brain), and a full suite of 12 DeFi and social protocols. Built from scratch with privacy and user empowerment at its core.

## Полное описание (Long Description)
> AIX OS is not just a cryptocurrency; it is an ecosystem designed to make technology serve human happiness. The project is built on a custom Proof-of-Work blockchain (ECDSA secp256k1, SHA-256) with a maximum supply of 21 billion tokens and zero pre-mine. 
> 
> Key features include:
> - **AIX Brain:** A native AI assistant that lives in your wallet. Users can execute blockchain transactions using natural language.
> - **12 Unique Protocols:** Including Dead Man's Switch (blockchain inheritance), Proof of Contribution (rewarding open-source developers), AIX Contacts (sending crypto by phone number), and an internal AMM Swap.
> - **Mobile-First Approach:** A Flutter-based mobile wallet that can run a fully autonomous local node, mine blocks, and sync offline.
> - **Messenger:** A decentralized chat built directly on blockchain transactions.

## Токеномика
*   **Allocation:** 100% mined by the community (PoW).
*   **Block Reward:** 50 AIX (halving every 210,000 blocks).
*   **Transaction Fee:** 0.1% (goes to the miner).

## Ссылки
*   **Website:** https://aix-os.github.io
*   **GitHub:** https://github.com/aix-os/aix-os
*   **Whitepaper:** https://github.com/aix-os/aix-os/blob/main/docs/WHITEPAPER.md
*   **Telegram:** (Добавь ссылку, когда создашь)
*   **Twitter (X):** (Добавь ссылку, когда создашь)
"""

# =============================================================================
# 2. BSC_WRAPPING_GUIDE.md
# =============================================================================
dex_guide = """# 🌉 Инструкция: Как вывести AIX на PancakeSwap (BSC)

Чтобы AIX попал на CoinGecko и CMC, нам нужно создать торговую пару. Мы сделаем это через обернутый токен **wAIX** в сети Binance Smart Chain (BSC), так как там низкие комиссии.

## Шаг 1. Развертывание контракта wAIX (BEP-20)
1. Перейди на [Remix IDE](https://remix.ethereum.org).
2. Создай новый файл `wAIX.sol`.
3. Вставь этот код (стандартный токен OpenZeppelin):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract WrappedAIX is ERC20 {
    constructor() ERC20("Wrapped AIX", "wAIX") {
        _mint(msg.sender, 21000000000 * 10**18); // 21 млрд
    }
}