# ZULU.cash Build Log  
_Tracking the public evolution of the ZULU prototype._

---

## Day 1 — Concept & Naming

- Sketched the initial idea: private AI agent for Zcash shielded payments  
- Defined high-level vision:
  - Local AI
  - Encrypted ledger
  - No cloud, no telemetry  
- Chose the name **ZULU** and registered `zulu.cash`  
- Created initial GitHub repo structure

---

## Day 2 — Payment Flow & Architecture v1

- Designed the first **ZEC → USDC** settlement flow  
- Selected **NEAR** as the cross-chain settlement layer  
- Drafted Architecture v1:
  - ZEC watch-only detection
  - Local ledger
  - Basic swap engine concept  
- Identified key constraints:
  - ZULU must remain non-custodial
  - ZULU must never hold private keys

---

## Day 3 — Prototype + Website

- Wired up:
  - Local AI (Ollama + Phi-3 Mini)  
  - Encrypted SQLCipher ledger (stub)  
  - ZEC watcher (lightwalletd client scaffold)  
- Launched first version of the marketing site at **https://zulu.cash**  
- Started positioning: "Intelligence Without Surveillance"

---

## Day 4 — Litepaper + Directional Alignment

- Wrote **Litepaper v0.3** and committed to `/docs/litepaper.md`  
- Created **investor one-pager** for ecosystem / grant conversations  
- Updated website copy to highlight:
  - ZEC → USDC swaps
  - Merchant settlement
  - Build-in-public approach  
- Finalized repo structure for:
  - `/backend`
  - `/frontend`
  - `/docs`
  - `/demo`

---

## Day 5 — ZEC → USDC Engine (Design)

- Drafted NEAR-based swap engine module  
- Sketched interface for:
  - `createInvoice()`
  - `detectPayment()`
  - `forwardToSwap()`
  - `recordSettlement()`  
- Defined risk & safety checks:
  - Minimum confirmations
  - Amount thresholds
  - Rate sanity checks

---

## Day 6 — Merchant & UX Paths

- Defined **merchant experience**:
  - QR invoices
  - USDC settlement view
  - Private ledger of payouts  
- Defined **user experience**:
  - Scan → pay in ZEC
  - Local AI for ledger questions  
- Updated website sections:
  - "How It Works"
  - "For Merchants"
  - Terminal demo snippet

---

## Day 7+ — In Progress

- Implementing:
  - First working end-to-end test (testnet)  
  - Sample `sample-wallet.json` + `sample-queries.txt`  
  - Backend routes for AI queries + TX listing  
- Exploring:
  - Future MPC integration for private analytics
  - Third-party regulated merchant onboarding (partner TBA)

---

_This log will continue to be updated as milestones land.  
New entries should be appended chronologically with date + focus._
