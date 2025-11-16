# 🗂️ ZULU Repository Structure - Complete File Map

This document shows the complete file structure for the ZULU.cash repository.
All files from `/mnt/user-data/outputs/` should be placed according to this structure.

```
zulu/
│
├── README.md                          ← Main repository README (from outputs/README.md)
├── LICENSE                            ← MIT License (from outputs/LICENSE)
├── .gitignore                         ← Git ignore rules (from outputs/.gitignore)
├── SECURITY.md                        ← Security policy (from outputs/SECURITY.md)
├── CONTRIBUTING.md                    ← Contribution guidelines (from outputs/CONTRIBUTING.md)
│
├── docs/
│   ├── litepaper.md                   ← Technical litepaper (from outputs/litepaper.md)
│   ├── investor-one-pager.md          ← Investor pitch (from outputs/investor-one-pager.md)
│   ├── build-log.md                   ← Public build log (from outputs/build-log.md)
│   └── architecture-diagram.md        ← Architecture docs (from outputs/architecture-diagram.md)
│
├── backend/
│   ├── README.md                      ← Backend docs (from outputs/backend-README.md)
│   ├── package.json                   ← Backend dependencies (from outputs/backend-package.json)
│   ├── .env.example                   ← Environment template (from outputs/.env.example)
│   ├── .env                           ← Your local config (create from .env.example)
│   ├── tsconfig.json                  ← TypeScript config (create manually)
│   │
│   └── src/
│       ├── server.ts                  ← Main server entry point
│       │
│       ├── ai/
│       │   ├── ollamaClient.ts        ← Ollama integration
│       │   ├── queryEngine.ts         ← NL → SQL converter
│       │   └── index.ts
│       │
│       ├── ledger/
│       │   ├── sqlcipher.ts           ← Encrypted DB client
│       │   ├── transactionParser.ts   ← TX data parser
│       │   ├── schema.sql             ← Database schema
│       │   └── index.ts
│       │
│       ├── zec/
│       │   ├── lightwalletdClient.ts  ← Zcash RPC client
│       │   ├── txWatcher.ts           ← Transaction watcher
│       │   ├── viewKeyManager.ts      ← View key handler
│       │   └── index.ts
│       │
│       ├── near/
│       │   ├── nearClient.ts          ← NEAR RPC client
│       │   ├── swapEngine.ts          ← ZEC → USDC swap logic
│       │   ├── settlementTracker.ts   ← Track settlements
│       │   └── index.ts
│       │
│       ├── merchant/
│       │   ├── qrGenerator.ts         ← QR code creation
│       │   ├── invoiceManager.ts      ← Invoice logic
│       │   ├── paymentStatus.ts       ← Payment tracking
│       │   └── index.ts
│       │
│       ├── utils/
│       │   ├── pricing.ts             ← Price oracle
│       │   ├── logger.ts              ← Logging utility
│       │   ├── validation.ts          ← Input validation
│       │   └── config.ts              ← Config management
│       │
│       └── routes/
│           ├── health.ts              ← Health check
│           ├── transactions.ts        ← TX endpoints
│           ├── ai.ts                  ← AI query endpoints
│           ├── invoice.ts             ← Invoice endpoints
│           └── swap.ts                ← Swap endpoints
│
├── frontend/
│   ├── package.json                   ← Frontend dependencies (from outputs/frontend-package.json)
│   ├── tsconfig.json                  ← TypeScript config
│   ├── next.config.js                 ← Next.js config
│   ├── tailwind.config.js             ← Tailwind config
│   ├── postcss.config.js              ← PostCSS config
│   │
│   ├── public/
│   │   ├── favicon.ico                ← From outputs/zulu-favicon.ico
│   │   ├── zulu-favicon.svg           ← From outputs/zulu-favicon.svg
│   │   ├── zulu-favicon-16.png        ← From outputs/
│   │   ├── zulu-favicon-32.png        ← From outputs/
│   │   ├── zulu-favicon-180.png       ← From outputs/
│   │   ├── zulu-favicon-192.png       ← From outputs/
│   │   ├── zulu-favicon-512.png       ← From outputs/
│   │   └── site.webmanifest           ← From outputs/site.webmanifest
│   │
│   └── app/
│       ├── layout.tsx                 ← Root layout
│       ├── page.tsx                   ← Landing page (from outputs/zulu-landing.html - convert to React)
│       ├── globals.css                ← Global styles
│       │
│       ├── chat/
│       │   └── page.tsx               ← AI chat interface
│       │
│       ├── merchant/
│       │   └── page.tsx               ← Merchant terminal
│       │
│       └── components/
│           ├── ChatUI.tsx             ← Chat component
│           ├── MerchantTerminal.tsx   ← Terminal component
│           ├── PaymentQR.tsx          ← QR display
│           ├── TransactionList.tsx    ← TX history
│           └── Header.tsx             ← Site header
│
├── demo/
│   ├── sample-wallet.json             ← Sample wallet data (from outputs/sample-wallet.json)
│   ├── sample-queries.txt             ← Example AI queries (from outputs/sample-queries.txt)
│   └── walkthrough.mp4                ← Demo video (create later)
│
└── scripts/
    ├── setup.sh                       ← Setup script (from outputs/setup.sh - make executable!)
    └── test-swap.ts                   ← Test swap integration
```

## 📋 File Checklist

### ✅ Root Level Files
- [ ] README.md
- [ ] LICENSE
- [ ] .gitignore
- [ ] SECURITY.md
- [ ] CONTRIBUTING.md

### ✅ Documentation Files (docs/)
- [ ] litepaper.md
- [ ] investor-one-pager.md
- [ ] build-log.md
- [ ] architecture-diagram.md

### ✅ Backend Files (backend/)
- [ ] README.md
- [ ] package.json
- [ ] .env.example
- [ ] Create .env from .env.example

### ✅ Frontend Files (frontend/)
- [ ] package.json
- [ ] All favicon files in public/
- [ ] site.webmanifest
- [ ] Convert zulu-landing.html to React components

### ✅ Demo Files (demo/)
- [ ] sample-wallet.json
- [ ] sample-queries.txt

### ✅ Scripts (scripts/)
- [ ] setup.sh (make executable with `chmod +x`)

## 🚀 Quick Setup Commands

```bash
# 1. Create the directory structure
mkdir -p zulu/{docs,backend/src/{ai,ledger,zec,near,merchant,utils,routes},frontend/{app,public},demo,scripts}

# 2. Copy all files from outputs to their correct locations
# (See structure above for exact paths)

# 3. Make setup script executable
chmod +x scripts/setup.sh

# 4. Run setup
./scripts/setup.sh

# 5. Start developing!
```

## 📝 Notes

**Files to create manually:**
- Backend TypeScript config: `backend/tsconfig.json`
- Frontend Next.js config: `frontend/next.config.js`
- Frontend Tailwind config: `frontend/tailwind.config.js`
- All source files in `backend/src/` (scaffolds provided in backend README)
- React components for frontend (convert from landing page HTML)

**Files already generated:**
- All documentation (README, litepaper, etc.)
- Package.json files
- Demo data
- Favicon assets
- Environment template

**Next steps:**
1. Copy all files to their correct locations
2. Run `./scripts/setup.sh`
3. Start building the actual implementation!

---

*Built for Zypherpunk Hackathon • "Intelligence Without Surveillance"*
