# 🌍 English posts for HN / Reddit

---

## Hacker News — Show HN

**Title:**
```
Show HN: AIX OS – A decentralized OS with a local LLM that actually acts
```

**Body (first comment, when submitting):**

```
Hi HN,

I built AIX OS — a decentralized operating system + a local LLM that
can actually perform actions on the system. You say "send 5 AIX to mom"
and it does, without you touching a form.

Three layers:
  🧠 AIX Brain   — local LLM (Ollama), tool-calling, 19 tools
  🛡 12 protocols — gift, timelock, inheritance, reputation, swap, PoC, ...
  ⛓ Core chain   — PoW, ECDSA secp256k1, 21M max supply, no pre-mine

Why it's safe:
  - The LLM NEVER sees the private key. Keys live behind a signer layer,
    read only at the moment of signing, only after explicit y/N confirmation.
  - HTTP API uses NullSigner — cannot send. Only CLI can, and only with
    human confirmation.
  - Test `test_no_private_key_leak_in_any_result` proves no tool result
    contains the word "private_key".

Runs on 8 GB RAM (qwen2.5:3b via Ollama). Everything local — no cloud,
no telemetry, no external DB.

77 tests passing. MIT license. Python 3.11+.

Repo: https://github.com/aix-os/aix-os
Landing: (add if you host it)
Whitepaper: https://github.com/aix-os/aix-os/blob/main/docs/WHITEPAPER.md

Would love feedback on:
  1. The tool-calling security model — is NullSigner/CLISigner the right split?
  2. State sync between nodes — currently event-based, any better patterns?
  3. Naming — "OS" feels earned or premature?

Thanks!
```

---

## Reddit — r/LocalLLaMA

**Title:**
```
Built a local-LLM tool-calling layer where the private key physically can't leak
```

**Body:**

```
Hey r/LocalLLaMA,

I've been working on a decentralized OS ("AIX OS") with a local LLM as the
main interface. The interesting part for this sub: the security model for
tool-calling on a blockchain wallet.

Setup:
- Ollama, qwen2.5:3b (fits in 7 GB RAM), 19 tools via /api/chat with `tools` param
- Tools: chain_status, wallet_balance, dao_list, poc_stats, ai_memory_*,
  preview_send, safe_send, gift_*, timelock_*, swap_*, sbt_award, id_register

The hard part: letting the LLM *send money* without letting it *see the key*.

My approach:
1. Two signer implementations:
   - NullSigner: used by HTTP API. Every send attempt returns "disabled".
   - CLISigner: used by `aix brain chat --wallet alice`. Reads the key file
     only after the user presses y.
2. The LLM never receives the key. The `safe_send` tool takes
   (recipient, amount) only. Key is loaded inside CLISigner.confirm_and_send.
3. Write operations that don't need a signature (gift, timelock) use
   `confirm_action(preview, "gift_create")` — same y/N gate, no key at all.
4. A test asserts the string "private_key" never appears in any tool result.

Real demo (from a session):
  you> send 1 AIX to bob
  🧠 Brain thinks... → safe_send(recipient="bob", amount_aix=1.0)
  ┌─── SEND CONFIRMATION ────────────
  │ From: alice, To: @bob, Amount: 1.0 AIX
  │ Balance: 200.0 → 199.0 AIX
  └───────────────────────────────────
  Send? [y/N] y
  ✅ Sent. TX: dec9b1b3...

Everything is MIT, ~5k LOC Python. Repo: https://github.com/aix-os/aix-os

Curious how others here handle tool-calling + side effects. Especially:
- Do you gate every write, or trust the LLM for some categories?
- Any patterns for confirming via a preview vs a typed phrase?

Thanks!
```

---

## Reddit — r/cryptocurrency (осторожно, там жёстко)

**Title:**
```
Not another DeFi token — a decentralized OS with a local LLM. Here's what I built.
```

**Body:**

```
I know r/cryptocurrency is tired of ICOs. This is not that.

I built AIX OS — a decentralized OS for life. No token sale. No pre-mine.
21M max supply, PoW, 0 premined. Code is MIT.

The interesting part is not the token — it's the interface.

Instead of memorizing a wallet UI, you talk to the system:
  "send 5 AIX to mom" → it does
  "freeze 10 AIX until 2027" → it does
  "give bob an EARLY_BIRD medal" → it does

The LLM is local (Ollama). It never sees the private key. A signer layer
+ y/N confirmation gates all writes. There's a test proving the key
never leaks into tool results.

12 protocols: gift, timelock, dead-man's-switch (inheritance), reputation
(SBT), phone→address (contacts), AMM swap, proof-of-contribution, AI memory
on-chain, DAO.

77 tests. Python. Runs on 8 GB RAM.

Repo: https://github.com/aix-os/aix-os

I'm not asking for money. I'm asking for feedback on the design. Does this
solve a real problem for you, or is it a solution looking for one?
```

---

## Советы по английскому

1. **Не переводи заголовок дословно** — англоязычная аудитория любит прямоту
2. **Первое предложение — самая суть** — если не зацепит, дальше не читают
3. **Прямо говори «не ICO»** — на r/cryptocurrency без этого не откроют
4. **Не пиши «revolutionary», «game-changing»** — это красный флаг
5. **Заканчивай вопросом** — HN и Reddit любят дискуссию, а не монолог

---

## Тайминг

| День | Площадка | Почему |
|------|----------|--------|
| 7 | r/LocalLLaMA | Дружелюбны к LLM-проектам |
| 10 | HN Show HN | Смотрят на «показать что сделал» |
| 14 | r/cryptocurrency | Осторожно, там жёстко |

**После публикации:** оставайся в комментариях 2–3 часа. HN хоронит посты без ответа автора.