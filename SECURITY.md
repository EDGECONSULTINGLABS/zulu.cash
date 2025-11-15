# SECURITY POLICY — ZULU.cash

ZULU is a **local-first, non-custodial** prototype under active development.  
This document describes our current security model, assumptions, and how to report issues.

---

## 1. Security Model

### 1.1 Non-Custodial Design

- ZULU **never** asks for or stores:
  - Private spend keys
  - Seed phrases
  - Custodial balances
- ZULU only requires **incoming viewing keys** (IVKs) for Zcash shielded addresses.

### 1.2 Local-First Architecture

- AI model runs locally via **Ollama** (e.g. Phi-3 Mini)
- Ledger data is stored locally using **SQLCipher**-encrypted databases
- No centralized inference server is used

### 1.3 Limited External Dependencies

ZULU uses external endpoints for:

- `lightwalletd` — to fetch Zcash transaction data  
- NEAR RPC — to interact with swap contracts  
- Optional third-party merchant onboarding / payouts (TBA)  

We **do not** operate or control these services and recommend users treat them as potential metadata exposure points.

---

## 2. Threats We Aim to Mitigate

- Unauthorized access to local ledger data
- Accidental leakage of transaction history to third-party APIs
- Any requirement to share private keys with ZULU
- Centralized logging of user financial behavior

---

## 3. Threats Out of Scope (For Now)

ZULU is an evolving prototype. The following are currently out of scope:

- Adversarial model attacks (prompt injection, model poisoning)
- Side-channel attacks on device hardware
- Compromised device / malware at OS level
- Layer-1 protocol failures on Zcash or NEAR

As the project matures, these areas may be revisited.

---

## 4. Reporting a Vulnerability

If you believe you have found a security vulnerability in ZULU:

1. **Do not open a public GitHub issue.**  
2. Email a detailed report to:  
   **`team@edgeconsultinglabs.com`**  
3. Include:
   - Steps to reproduce
   - Impact (what can an attacker do?)
   - Any suggested remediation ideas

We will:

- Acknowledge receipt within **5 business days**
- Investigate and validate the issue
- Coordinate fix & disclosure where appropriate

---

## 5. Best Practices for Users

Until ZULU is hardened and audited:

- Treat it as an experimental tool, not a production wallet  
- Do **not** import large-value wallets  
- Use testnet where possible  
- Only connect to trusted `lightwalletd` and NEAR RPC endpoints  
- Keep your device OS and dependencies patched  

---

## 6. Disclaimer

ZULU is a work-in-progress prototype.  
No guarantees are made regarding security, suitability for any particular purpose, or regulatory compliance.  

Use at your own risk.
