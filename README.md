# 🛡️ NexusGuard: Autonomous General-Contractor Studio, Security Swarm & Cross-Chain Bounty Protocol on NEAR

[![Live Portal](https://img.shields.io/badge/Live%20Portal-Vercel-cyan.svg)](https://nexusguard-five.vercel.app)
[![Mission Control](https://img.shields.io/badge/Mission%20Control-Live%20App-emerald.svg)](https://nexusguard-five.vercel.app/app)
[![License: MIT](https://img.shields.io/badge/License-MIT-cyan.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![NEAR Protocol](https://img.shields.io/badge/NEAR-Protocol-green.svg)](https://near.org)
[![Tests Passing](https://img.shields.io/badge/Tests-54%2F54%20Passing-brightgreen.svg)](#-testing)
[![Dry-Run Safe](https://img.shields.io/badge/Mode-Dry--Run%20Safe-orange.svg)](#dry-run-mode)

> **A multi-agent AI studio that autonomously decomposes software projects, negotiates with specialist providers on [market.near.ai](https://market.near.ai), defends against prompt-injection attacks, and settles cross-chain payments via NEAR Intents—all governed by a policy-bound wallet that never touches a FullAccess key.**

---

## 🌐 Live Cloud Deployment (Vercel)

| Service | Direct Link | Description |
| :--- | :--- | :--- |
| **Public Landing Portal** | [https://nexusguard-five.vercel.app](https://nexusguard-five.vercel.app) | Dark-mode Web3 startup landing portal with live interactive terminal |
| **Mission Control Console** | [https://nexusguard-five.vercel.app/app](https://nexusguard-five.vercel.app/app) | Real-time multi-agent orchestrator, NEAR Testnet block monitor & threat matrix |
| **System Health API** | [`/api/health`](https://nexusguard-five.vercel.app/api/health) | Uptime & health check endpoint |
| **Wallet Policy & Keys API** | [`/api/policy`](https://nexusguard-five.vercel.app/api/policy) | Live scoped FunctionCall Access Key & NEAR Testnet RPC status |
| **Settlement Receipts API** | [`/api/receipts`](https://nexusguard-five.vercel.app/api/receipts) | NEAR Intents 1Click cryptographic receipts |
| **Accounting Ledger Export** | [`/api/ledger.csv`](https://nexusguard-five.vercel.app/api/ledger.csv) | Downloadable accountant CSV audit trail |

---

## 🏆 Hackathon Tracks Covered

| Track | Focus | Module |
|-------|-------|--------|
| **`07-agents`** | Autonomous agent orchestration, market.near.ai integration, negotiation | `crew_studio.py`, `agent_market.py`, `negotiation.py` |
| **`06-security`** | Prompt-injection defense, key custody, policy engine | `wallet_policy.py`, `security_swarm.py` |
| **`05-swarms`** | Multi-agent swarm coordination | `crew_studio.py`, `security_swarm.py` |
| **`04-business`** | Build-vs-buy task decomposition, accounting ledger | `crew_studio.py`, `pipeline.py` |
| **`08-realworld`** | Cross-chain settlement, verifiable receipts | `near_intents.py`, `pipeline.py` |
| **`01-defi`** | NEAR Intents 1Click cross-chain quotes | `near_intents.py` |

---

## 🚀 Quick Start (< 2 minutes)

### Prerequisites
- Python 3.11+
- No API keys or funded wallets required (everything runs in `--dry-run` mode)

### Setup

```bash
# Clone and enter the project
cd nexusguard

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# (Optional) Copy .env.example to .env and add API keys for LLM-powered decomposition
cp .env.example .env
```

### Do X → See Y

#### 1. Run the Full Pipeline
```bash
python main.py --dry-run
```
**→ See:** Policy-bound wallet initialization, 3-task decomposition, 3 negotiation scenarios (WALKED_AWAY, ACCEPTED_COUNTER, ACCEPTED_INITIAL), QA verification, cross-chain settlement receipts, and exported `receipts.json` + `accounting_ledger.csv`.

#### 2. Run the Attack Simulation
```bash
python main.py --attack-demo
```
**→ See:** A rogue agent reads a poisoned smart-contract comment, attempts to drain $50.00 USDC to a blocklisted address. The Security Swarm detects 5+ prompt-injection patterns, blocks the transaction, and emits a cryptographic incident receipt with a SHA-256 hash.

#### 3. Run Both Together
```bash
python main.py --dry-run --attack-demo
```

#### 4. Get JSON Output
```bash
python main.py --dry-run --json | python -m json.tool
```

#### 5. Run the Test Suite
```bash
pytest tests/ -v
```
**→ See:** 54 passing tests covering policy blocks, negotiation outcomes, attack defense, 1Click receipts, serverless ASGI routing, and all API endpoints.

#### 6. Launch the Web Dashboard
```bash
python server.py
# Open http://localhost:8000
```
**→ See:** High-contrast Tailwind Mission Control dashboard with buttons for "Run Full Pipeline" and "Simulate Prompt-Injection & Malicious Drain Attack".

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   NexusGuard Pipeline Orchestrator                │
│                        (pipeline.py)                             │
├──────────┬───────────┬──────────────┬───────────┬────────────────┤
│ Wallet   │ Crew      │ Agent Market │ Negotia-  │ Security       │
│ Policy   │ Studio    │ Integration  │ tion      │ Swarm          │
│ Engine   │ (Decomp)  │ (market.     │ Engine    │ (Risk Score +  │
│          │           │  near.ai)    │ (1-round) │  Attack Block) │
├──────────┴───────────┴──────────────┴───────────┴────────────────┤
│                    NEAR Intents 1Click API                        │
│              (Cross-Chain Settlement, dry=true)                   │
├──────────────────────────────────────────────────────────────────┤
│   receipts.json          │        accounting_ledger.csv           │
└──────────────────────────┴───────────────────────────────────────┘
```

---

## 🔐 Key Custody & Policy Engine

NexusGuard **never uses raw `FullAccess` keys**. The `PolicyBoundWallet` models a NEAR Function-Call Access Key scoped to the escrow contract:

```python
from src.wallet_policy import PolicyBoundWallet

wallet = PolicyBoundWallet()
print(wallet.get_access_key_info())
# → { "key_type": "FunctionCall", "scope": { "receiver_id": "escrow.nexusguard.testnet", ... } }

print(wallet.policy.describe_constraints())
# → Budget cap: $25.00, Human gate: $10.00, Cannot: delete_account, add_key, ...
```

**Policy Enforcements:**
- ✅ Budget cap: $25.00 USDC total
- ✅ Human-approval gate: Single payouts > $10.00 require human sign-off
- ❌ Cannot call `delete_account`, `add_key`, `delete_key`, `deploy_contract`, `stake`
- ❌ Cannot transfer to unapproved contracts
- ❌ Cannot exceed budget cap

---

## 🤝 1-Round Counter-Offer Negotiation

The negotiation engine runs exactly three demo scenarios:

| Provider | Quote | Budget | Outcome |
|----------|-------|--------|---------|
| `sec-swarm-alpha.near` | $9.50 | $6.00 | **WALKED_AWAY** (exceeds 10% buffer ceiling) |
| `audit-bot-lite.near` | $6.80 | $6.00 | **ACCEPTED_COUNTER** (countered at $6.60, accepted) |
| `verifier-alice.base.eth` | $4.75 | $5.00 | **ACCEPTED_INITIAL** (under budget) |

---

## 🚨 Attack Defense Demo

The `--attack-demo` flag simulates:
1. A rogue sub-agent reads poisoned contract code with embedded prompt-injection payloads
2. It attempts to drain $50.00 USDC to `0xDEADBEEF...BAD` (a blocklisted address)
3. The Counterparty Risk Scorer detects multiple CRITICAL signals
4. The Policy Engine blocks the transaction
5. A cryptographic Security Incident Receipt (SHA-256) is emitted

---

## 📋 Agent Market Disclosure

Per the `07-agents` track requirements, NexusGuard transparently discloses:

> **Public agent discovery** on market.near.ai is **OPEN** — any agent/user can browse.
> **Programmatic job creation** (escrow, MCP) **REQUIRES_AUTH** — authenticated credentials needed.
> **Dry-run mode** uses a **deterministic local bid simulator** — no live API credentials needed.

---

## 💸 Cross-Chain Settlement

Settlement uses the real **NEAR Intents 1Click API** at `https://1click.chaindefuser.com/v0/quote` with `"dry": true` (zero real funds). Falls back to deterministic offline hashing when rate-limited.

Outputs:
- **`receipts.json`** — Verifiable task receipts with intent quote IDs
- **`accounting_ledger.csv`** — Accountant-ready CSV with all required fields

---

## 📁 Repository Structure

```
.
├── README.md                        # Project documentation & live links
├── LICENSE                          # MIT License
├── .gitignore
├── .env.example                     # Template for API keys (optional)
├── requirements.txt                 # Python dependencies
├── vercel.json                      # Vercel serverless deployment config
├── Dockerfile                       # Container deployment config (Railway / Fly.io)
├── render.yaml                      # Render Blueprint deployment config
├── Procfile                         # Standard cloud web process runner
├── main.py                          # Rich CLI runner (--dry-run, --attack-demo)
├── server.py                        # FastAPI backend + Mission Control UI + ASGI normalizer
├── api/
│   └── index.py                     # Vercel serverless entrypoint
├── src/
│   ├── __init__.py
│   ├── wallet_policy.py             # Function-Call Access Key & policy engine
│   ├── negotiation.py               # 1-round counter-offer state machine
│   ├── security_swarm.py            # Risk scorer & prompt-injection interceptor
│   ├── crew_studio.py               # Multi-agent task decomposition
│   ├── pipeline.py                  # End-to-end orchestrator
│   └── integrations/
│       ├── __init__.py
│       ├── agent_market.py          # market.near.ai probe & disclosure
│       └── near_intents.py          # 1Click API cross-chain adapter
├── static/
│   ├── landing.html                 # Dark-mode Web3 startup landing portal
│   └── index.html                   # High-contrast Mission Control dashboard
└── tests/
    └── test_nexus_suite.py          # 54 automated pytest tests
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --tb=short

# Run specific test class
pytest tests/test_nexus_suite.py::TestSecuritySwarm -v
```

All tests run deterministically with **zero API keys, zero funded wallets, and zero network dependencies**.

---

## 🔧 Configuration

Copy `.env.example` to `.env` and optionally fill in:

| Variable | Purpose | Required? |
|----------|---------|-----------|
| `NEAR_AI_API_KEY` | NEAR AI Cloud LLM endpoint | No (fallback to deterministic) |
| `GROQ_API_KEY` | Groq LLM endpoint | No |
| `GEMINI_API_KEY` | Google Gemini endpoint | No |
| `NEAR_ACCOUNT_ID` | NEAR testnet account | No (default: nexusguard.testnet) |

---

## 📜 License

MIT License — see [LICENSE](LICENSE).
