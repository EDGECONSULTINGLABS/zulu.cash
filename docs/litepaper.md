# ZULU.cash Litepaper v0.3  
**Private AI Agent for Zcash Shielded Payments & Cross-Chain Settlement**

---

## 1. Abstract

ZULU is a private, local-first AI agent that lets users pay with **shielded ZEC** while merchants receive **USDC** – without surveillance, centralized custody, or cloud-hosted AI models.

Built during the **Zypherpunk Zcash Hackathon**, ZULU combines:

- Zcash shielded transactions  
- Local AI (Phi-3 Mini via Ollama)  
- Encrypted on-device ledger (SQLCipher)  
- Cross-chain ZEC → USDC settlement (via NEAR-based swap engine)  

ZULU's core idea:  
> **AI should understand your money without exposing your money.**

---

## 2. Motivation

### 2.1 Problem: AI + Finance = Surveillance by Default

Modern AI systems rely on centralization:
- Cloud models
- Central data lakes
- Continuous telemetry

If *those* systems sit between users and their money:

- Every payment becomes training data  
- Every account becomes a behavioral profile  
- Every merchant becomes a dataset  

This breaks the core values of **Zcash** and privacy-preserving finance.

### 2.2 Opportunity: Private AI for Private Money

Zcash already provides:
- Shielded transactions  
- Proven cryptography  
- Strong privacy guarantees  

ZULU adds:
- Local understanding  
- Natural language queries  
- Merchant-grade UX  
- Cross-chain settlement  

Without:  
- Cloud logs  
- KYC for users  
- Centralized data brokers  

---

## 3. High-Level Design

ZULU has three main actors:

1. **User** – Pays in shielded ZEC from their own wallet  
2. **ZULU Agent** – Local AI + encrypted ledger + detectors  
3. **Merchant** – Accepts ZEC, settles in USDC

### 3.1 Core Principles

- **Local-first**: All AI logic runs on-device  
- **View-only**: Only incoming viewing keys are ever used  
- **Non-custodial**: ZULU never holds funds or keys  
- **Composable**: Swap and onboarding happen via external protocols/partners  
- **Transparent**: Source, architecture, and roadmap are public

---

## 4. ZEC → USDC Settlement Flow

1. User scans a merchant invoice (QR with amount in USD)
2. ZULU displays the equivalent ZEC amount
3. User pays from their own Zcash wallet (shielded TX)
4. ZULU detects the incoming shielded payment via view key
5. Once confirmed, ZULU forwards ZEC to a **NEAR-based swap module**
6. Smart contracts swap **ZEC → USDC**
7. Merchant receives USDC in their settlement account

**Key Separation:**

- ZULU = local agent, ledger, and detection  
- NEAR = on-chain swap + routing  
- Third-party (TBA) = optional regulated merchant onboarding  

---

## 5. Architecture Overview

### 5.1 Components

- **Local AI Engine**
  - Phi-3 Mini via Ollama
  - Runs entirely on user device
  - Used for ledger Q&A, anomaly hints, human-readable summaries

- **Encrypted Ledger**
  - SQLCipher-backed DB
  - Stores:
    - ZEC transaction summaries
    - Pricing snapshots
    - Merchant invoices
    - Swap results
  - Always encrypted at rest

- **Zcash Watchers**
  - Connect to `lightwalletd`
  - Subscribe using incoming viewing keys
  - No spending keys imported

- **Swap Engine (Prototype)**
  - Offloads ZEC → USDC conversion to NEAR contracts
  - ZULU simply constructs and forwards transactions

- **Future: Private Compute Layer (MPC / Nillion-like)**
  - Privacy-preserving analytics on encrypted data
  - Pattern detection, routing decisions, risk scores
  - Without exposing raw user or merchant data

---

## 6. Privacy Model

### 6.1 What ZULU Sees

- Encrypted transaction metadata
- Viewing-only information
- Locally stored ledger features

### 6.2 What ZULU Never Sees

- Private spend keys  
- Raw wallet seed phrases  
- User PII or KYC data  
- Merchant's bank login or custodial info  

### 6.3 Cloud Exposure

- No cloud inference  
- No hosted LLMs  
- No centralized logs  
- No remote analytics  

The only external calls are:
- To `lightwalletd` for ZEC tx data
- To NEAR RPC / swap contracts for settlement
- (Future) To a regulated third-party onboarding provider for merchants (TBA)

---

## 7. Roadmap

### Phase 1 — Prototype (Hackathon)
- Local AI (Phi-3 Mini)
- Encrypted ledger
- Basic watch-only detection
- ZEC → USDC swap flow prototype
- Public website and docs

### Phase 2 — Merchant POS
- Merchant invoice generator
- QR-based payment requests
- Real-time detection + status
- Simple settlement dashboard

### Phase 3 — Private Compute Layer
- MPC-based analytics on encrypted data
- Spending pattern clustering
- Swap-routing recommendations
- Private risk signals

### Phase 4 — Merchant Onboarding (Third-Party Partner)
- Optional business onboarding via regulated provider
- USDC payout rails
- Compliant reporting
- ZULU remains non-custodial and local-first

---

## 8. Status & Contributions

ZULU is under active development and built fully in public.

- Code: https://github.com/edgeconsultinglabs/zulu  
- Site: https://zulu.cash  
- X/Twitter: https://x.com/MyCrypt0world  

We welcome contributions from:
- Zcash engineers  
- NEAR smart contract developers  
- Privacy & MPC researchers  
- AI/LLM systems engineers  
- UX & product designers  

---

## 9. Contact

**Founder:**  
Alula Zeryihun  
Edge Consulting Labs  

- Email: `team@edgeconsultinglabs.com`  
- X/Twitter: [@MyCrypt0world](https://x.com/MyCrypt0world)  

> If you're reading this, you're still early.
