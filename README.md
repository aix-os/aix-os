<div align="center">

# ⚡ AIX OS

**The operating system for life.**

A decentralized blockchain + a built-in AI companion that actually understands you.
You speak — it acts. Your keys never leave your machine.

*«Technology should make people happier — not richer.»*

</div>

---

## 🧠 What is AIX OS?

Most crypto projects ask you to **learn their UI**. AIX OS asks you to **speak your language**.

Tell it *"send 5 AIX to mom"* — and it does. No forms, no buttons, no seed-phrase anxiety. Just words.

Under the hood it's three layers stacked into one coherent system:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   🧠  AIX BRAIN           Local LLM (Ollama) + tool-calling    │
│       ───────────         "send 5 AIX to bob" → safe_send()    │
│                           Private key NEVER reaches the LLM    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   🛡  12 PROTOCOLS        Gift · TimeLock · SBT · Lottery ·    │
│       ────────────        DMS · AIX-ID · Burn-to-Mint ·        │
│                           Contacts · Swap-AMM · PoC ·          │
│                           State-Sync · AI Memory                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ⛓   CORE BLOCKCHAIN     PoW · ECDSA secp256k1 ·             │
│       ─────────────       AIX-addresses · No pre-mine          │
│                           21 000 000 000 max · 50 AIX reward       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Every layer is independently useful. Together — they're a life OS.

---

## 🎬 60-second demo (in words)

**Terminal:**

```powershell
$ .venv\Scripts\python.exe cli\main.py brain chat --wallet alice

🧠 AIX Brain — interactive mode (qwen2.5:3b)
   exit/quit — leave, reset — clear history

you> send 1 AIX to bob
🧠 Brain thinks...
┌─── SEND CONFIRMATION ────────────────────────────────
│ From:   alice (AIXTA5WAvDBAifiZuYfwfxM57Ajn8kGcG6xj2)
│ To:     @bob
│ Amount: 1.0 AIX
│ Balance: 200.0 → 199.0 AIX
└──────────────────────────────────────────────────────
Send? [y/N] y
✅ Sent. TX: dec9b1b3…  Broadcast to 1 peer.
🧠 Transaction sent. Will be processed by other nodes.

you> exit
```

**What just happened:**

1. You spoke in **natural language**.
2. The local LLM parsed intent and called the `safe_send` tool.
3. The tool built a preview — **before touching the key**.
4. You confirmed with `y/N`.
5. Only then the key was read from disk, tx signed, broadcast.

At no point did the LLM see the private key. Not in the prompt, not in the tools, not in the logs.

---

## 🔐 Why this is safe (really safe)

| Threat | Defence |
|---|---|
| LLM leaks the private key | The key lives behind `CLISigner`. LLM never sees it. |
| Prompt injection asks LLM to send | LLM has no signer — it can't send. Ever. |
| Attacker hits `/brain/ask` HTTP endpoint | HTTP agents get `NullSigner` — physically cannot send. |
| Wrong recipient via AIX-ID | Address validated: must start with `AIX`, length ≥ 30. |
| Silent send from "how much would it cost?" | A separate read-only tool `preview_send` exists. |

Read the tests to verify: `tests/test_brain_signer.py::test_no_private_key_leak_in_any_result`.

---

## 🚀 Quick start

### Requirements

- Python 3.11+
- [Ollama](https://ollama.com/download) (local LLM runtime)
- ~3 GB free disk for a small model

### Install

```bash
git clone https://github.com/aix-os/aix-os.git
cd AIX-OS

python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### Pull a model

```bash
ollama pull qwen2.5:3b      # 1.9 GB, fits in 8 GB RAM
```

### Run

```bash
# Windows: one-shot start of 2 nodes + web wallet
.\scripts\run_all.ps1

# Any OS: check that Brain sees the system
python cli/main.py brain health

# Talk to the OS
python cli/main.py brain chat --wallet alice
```

Web wallet: <http://localhost:9000>
Swagger API: <http://localhost:8010/docs>

### First words

```bash
python cli/main.py brain ask "What's the current chain height?"
# 🧠 The chain is currently 17 blocks tall.

python cli/main.py brain ask "Send 1 AIX to bob"
# → shows preview, asks y/N, only then sends
```

---

## 🧠 AIX Brain in 5 layers

```
ai/brain/
├── config.py         — env-based config (model, URL, timeout)
├── client.py         — HTTP client to Ollama (no agent logic)
├── tools.py          — 8 tools with JSON schemas for tool-calling
├── memory_bridge.py  — in-process bridge to AI Memory (#AI-1)
├── signer.py         — BaseSigner / NullSigner / CLISigner
└── agent.py          — orchestrator: LLM ↔ tools ↔ answer
```

**Tools available to the LLM:**

| Tool | Purpose | Safe? |
|---|---|---|
| `chain_status` | Node status: height, mempool, peers | read-only |
| `wallet_balance` | Balance of any AIX address | read-only |
| `dao_list` | DAO proposals with statuses | read-only |
| `poc_stats` | Proof of Contribution fund stats | read-only |
| `ai_memory_remember` | Write to AI Memory | in-process |
| `ai_memory_brief` | Read AI Memory summary | in-process |
| `preview_send` | Simulate a transaction (no side effects) | always allowed |
| `safe_send` | **Actually send AIX** — requires CLI signer + y/N | gated |

---


## 📱 Mobile App (Flutter)

The mobile wallet is fully functional and includes:
- **Local Node** — mine, send, and sync blocks offline.
- **AIX Brain** — local LLM (Ollama) right in your pocket.
- **Messenger** — send text messages via blockchain transactions.
- **Live Prices** — real-time crypto rates via CoinGecko API.
- **12 Protocols** — DAO, Gifts, TimeLock, Swap, Contacts, Medals, and more.

## 🛠 Tech stack

| Layer | Tech |
|---|---|
| Language | Python 3.11+ |
| API | FastAPI + Uvicorn |
| Crypto | `ecdsa` secp256k1, `base58` |
| LLM | Ollama (local, any model) |
| Web UI | Vanilla JS + Chart.js |
| CLI | argparse + colorama + tabulate |
| Storage | JSON files (no external DB) |

**Zero external databases. Zero cloud. Zero telemetry.** Everything runs on your machine.

---

## 📊 Project status

- ✅ Core blockchain (PoW, ECDSA, Base58Check `AIX…` addresses)
- ✅ 12 protocols implemented in mobile UI in mobile UI
- ✅ AI Memory (#AI-1) — blockchain-native memory for AI
- ✅ AIX Brain (#AI-2) — local LLM with tool-calling
- ✅ Safe Send (#AI-3) — CLI-gated transactions with `y/N`
- ✅ Brain Mobile UI — full chat in Flutter
- ✅ 58 tests passing
- ✅ Live CoinGecko prices (BTC, ETH, etc.)
- 🟡 Demo GIF / video
- 🚧 ZK proofs, LoRa mesh, Flutter Android APK

---

## 🎯 Roadmap

**Near-term**
- [ ] English + Russian landing with live node stats
- [ ] Demo GIF: "I speak — the OS acts"
- [ ] Publish to Habr, VK, Telegram

**Mid-term**
- [ ] Mobile Flutter → Android APK
- [ ] Voice input (local Whisper) + voice output (Piper)
- [ ] ZK-proofs for private transactions

**Long-term**
- [ ] LoRa mesh — AIX OS without internet
- [ ] Decentralized AI training via PoC
- [ ] Real-world adoption: family inheritance, small business payments

---

## 🤝 Contributing

We welcome contributors. Ideas worth building:

- **New Brain tools** (see `ai/brain/tools.py`) — gift, timelock, swap, sbt.
- **Translations** — landing and docs.
- **Test coverage** — new protocols need test suites.
- **Voice interface** — Whisper + Piper integration.
- **Mesh networking** — LoRa / Reticulum.

Open an issue, propose a design, ship a PR.

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 💛 Credits

Built by the founder of AIX OS and an AI co-pilot, in public, from scratch, in 2026.

> *«Империя начинается с тебя.»*
> *«The empire starts with you.»*

<div align="center">

**If this resonates — star the repo. It helps more than you think.**

</div>