# 🛠️ ZULU Development Setup Guide

Complete guide to setting up ZULU.cash for local development and testing.

---

## ✅ 1. Windsurf Workspace Setup

### Clone Repository
```bash
git clone https://github.com/edgeconsultinglabs/zulu.cash
cd zulu.cash
```

### Install Recommended Extensions
Windsurf will auto-detect the workspace and prompt for extensions:
- ✅ Node.js
- ✅ TypeScript
- ✅ React
- ✅ MDX
- ✅ Tailwind CSS

Accept all recommended extensions.

---

## ✅ 2. Backend Setup (Local)

### Install Dependencies
```bash
cd backend
npm install
```

### Configure Environment
Create `backend/.env`:

```env
# Ollama local model
OLLAMA_MODEL=phi3:mini
OLLAMA_URL=http://localhost:11434

# Zcash
LIGHTWALLETD_URL=https://lightwalletd.testnet.z.cash:9067
ZCASH_NETWORK=testnet
INCOMING_VIEW_KEY=zxviewkeyXXXXXXXXXXXX

# SQLCipher vault
LEDGER_DB_PATH=./ledger/zulu.db
LEDGER_DB_PASSWORD=your_strong_password_here

# NEAR
NEAR_ENV=testnet
NEAR_ACCOUNT_ID=your-testnet-account.testnet
NEAR_RPC_URL=https://rpc.testnet.near.org
NEAR_SWAP_CONTRACT=zulu-swap.testnet

# Pricing snapshots
COINGECKO_API=https://api.coingecko.com/api/v3/simple/price

# Server
PORT=4000
```

### Start Backend Server
```bash
npm run dev
```

Backend runs at: **http://localhost:4000**

Expected output:
```
🟣 ZULU Backend starting...
🔐 SQLCipher ledger initialized
🤖 Ollama connected (phi3:mini)
🟣 Watching for incoming shielded notes...
✅ Backend ready on http://localhost:4000
```

---

## ✅ 3. Frontend Setup (Local)

### Install Dependencies
```bash
cd frontend
npm install
```

### Configure Environment
Create `frontend/.env.local`:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:4000
NEXT_PUBLIC_ENV=local
```

### Start Frontend Server
```bash
npm run dev
```

Frontend runs at: **http://localhost:3000**

---

## ✅ 4. Connect to Zcash Testnet

### Get Testnet Wallet
1. **Create test ZEC wallet** using:
   - `zecwallet-lite-cli`
   - Or use testnet faucet: https://faucet.testnet.z.cash/

2. **You need:**
   - ✅ t-address (transparent)
   - ✅ z-address (shielded)
   - ✅ Incoming viewing key

### Configure Viewing Key
Paste your incoming viewing key into `backend/.env`:

```env
INCOMING_VIEW_KEY=zxviewkeyXXXXXXXXXXXX
```

### Restart Backend
```bash
npm run dev
```

Logs should show:
```
🟣 Watching for incoming shielded notes...
👁️ Monitoring address: ztestsapling1abc...
```

---

## ✅ 5. Setup NEAR Swap Test Environment

### Install NEAR CLI
```bash
npm install -g near-cli
```

### Login to NEAR
```bash
near login
```

### Create Test Accounts
```bash
near create-account zulu-swap.testnet --masterAccount your-testnet-account.testnet
```

### Deploy Mock Swap Contract (Optional)
```bash
near deploy --accountId zulu-swap.testnet --wasmFile ./contracts/swap_mock.wasm
```

### Update Environment
Add to `backend/.env`:
```env
NEAR_SWAP_CONTRACT=zulu-swap.testnet
```

### Test Contract
```bash
near view zulu-swap.testnet get_rate
```

---

## ✅ 6. Test the Local AI Agent

### 1️⃣ Ping AI Endpoint
```bash
curl http://localhost:4000/ai \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"What is my spending for November?"}'
```

**Expected Response:**
```json
{
  "response": "You have no ledger data yet. Start by receiving or sending ZEC."
}
```

### 2️⃣ Add Mock Ledger Entries
```bash
curl http://localhost:4000/ledger/add \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"amount": 0.5, "asset": "ZEC", "direction": "outgoing"}'
```

### 3️⃣ Query AI Again
```bash
curl http://localhost:4000/ai \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"What is my spending for November?"}'
```

**Expected Response:**
```json
{
  "response": "You spent 0.5 ZEC in November."
}
```

---

## ✅ 7. Simulate Full ZEC → USDC Settlement Flow

### Step 1: Send ZEC Testnet to Merchant
Send **0.01 tZEC** to the merchant watch-only address.

### Step 2: Backend Detects Transaction
Logs should show:
```
💰 Incoming shielded payment detected: 0.01 ZEC
📝 Transaction ID: abc123...
🔍 Confirmations: 0/3
```

### Step 3: Forward ZEC to Swap Engine
Backend automatically calls:
```bash
POST /swap/zec-to-usdc
```

### Step 4: NEAR Contract Returns USDC Amount
Log output:
```
🔁 Swap executed: 0.01 ZEC → 0.94 USDC (rate: 94)
⏳ NEAR tx pending...
✅ NEAR tx confirmed: txhash123...
```

### Step 5: Settlement Sent
Mock transfer simulates USDC delivery:
```
💵 USDC settlement: 0.94 USDC → merchant_account.testnet
✅ Settlement complete
```

### Manual Test (Optional)
```bash
curl http://localhost:4000/swap/zec-to-usdc \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 0.01,
    "merchantAccount": "merchant.testnet"
  }'
```

---

## ✅ 8. Deploy Production Builds

### Frontend (Next.js)
```bash
cd frontend
npm run build
npm start
```

Production server runs on **http://localhost:3000**

### Backend (Node)
```bash
cd backend
npm run build
npm start
```

Production server runs on **http://localhost:4000**

---

## ✅ 9. Deploy to Cloud Platforms

### Frontend → Vercel
```bash
cd frontend
vercel
```

**Add environment variables in Vercel dashboard:**
- `NEXT_PUBLIC_BACKEND_URL`
- `NEXT_PUBLIC_ENV=production`

### Backend → Fly.io
```bash
cd backend
fly launch
fly deploy
```

**Set secrets:**
```bash
fly secrets set LEDGER_DB_PASSWORD=your_secure_password
fly secrets set INCOMING_VIEW_KEY=zxviewkey...
fly secrets set NEAR_ACCOUNT_ID=zulu.testnet
```

### Backend → Render (Alternative)
1. Connect GitHub repo
2. **Build Command:** `npm install`
3. **Start Command:** `npm start`
4. Add environment variables in dashboard

---

## ✅ 10. Troubleshooting Cheatsheet

### ❌ AI not responding
**Problem:** Ollama not running

**Solution:**
```bash
ollama serve
ollama run phi3:mini
```

Verify:
```bash
curl http://localhost:11434/api/tags
```

---

### ❌ ZEC detection not working
**Problem:** Cannot connect to lightwalletd

**Solution:**
```bash
curl https://lightwalletd.testnet.z.cash:9067/v1/GetLatestBlock
```

Check `backend/.env`:
```env
LIGHTWALLETD_URL=https://lightwalletd.testnet.z.cash:9067
INCOMING_VIEW_KEY=zxviewkey... # Must be valid
```

---

### ❌ NEAR swap failing
**Problem:** Contract not deployed or misconfigured

**Solution:**
```bash
# Check contract exists
near view $NEAR_SWAP_CONTRACT get_rate

# Check account balance
near state $NEAR_SWAP_CONTRACT

# Re-deploy if needed
near deploy --accountId zulu-swap.testnet --wasmFile swap_mock.wasm
```

---

### ❌ Frontend cannot reach backend
**Problem:** CORS or URL misconfiguration

**Solution:**

Check `frontend/.env.local`:
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:4000
```

Check backend CORS settings in `backend/src/server.ts`:
```typescript
app.use(cors({
  origin: ['http://localhost:3000', 'https://zulu.cash'],
  credentials: true
}));
```

Test backend directly:
```bash
curl http://localhost:4000/health
```

---

### ❌ Database locked or corrupted
**Problem:** SQLCipher password wrong or DB corrupted

**Solution:**
```bash
# Delete and recreate (WARNING: loses data)
rm backend/ledger/zulu.db
npm run dev

# Or change password in .env and recreate
```

---

### ❌ Port already in use
**Problem:** 3000 or 4000 already taken

**Solution:**
```bash
# Find process
lsof -i :4000
# or on Windows
netstat -ano | findstr :4000

# Kill process
kill -9 <PID>

# Or change port in .env
PORT=5000
```

---

## 🔥 Quick Start (TL;DR)

```bash
# Clone repo
git clone https://github.com/edgeconsultinglabs/zulu.cash
cd zulu.cash

# Backend
cd backend
npm install
cp .env.example .env
# Edit .env with your keys
npm run dev

# Frontend (new terminal)
cd frontend
npm install
cp .env.local.example .env.local
npm run dev

# Start Ollama (new terminal)
ollama serve
```

**Open:** http://localhost:3000

---

## 📚 Additional Resources

- **Zcash Testnet Faucet:** https://faucet.testnet.z.cash/
- **NEAR Testnet Explorer:** https://explorer.testnet.near.org/
- **Ollama Models:** https://ollama.com/library
- **Lightwalletd Docs:** https://zcash.readthedocs.io/

---

## 🆘 Get Help

- **Issues:** https://github.com/edgeconsultinglabs/zulu.cash/issues
- **Discussions:** https://github.com/edgeconsultinglabs/zulu.cash/discussions
- **Email:** team@edgeconsultinglabs.com
- **X/Twitter:** [@MyCrypt0world](https://x.com/MyCrypt0world)

---

**Happy Building! 🚀**
