# ZULU Backend

Node.js + TypeScript backend for ZULU.cash private AI agent.

## Features

- 🤖 **Local AI Integration** - Ollama (Phi-3 Mini) for on-device intelligence
- 🔐 **SQLCipher Encrypted Ledger** - AES-256 encrypted transaction storage
- 🛡️ **Zcash Watch-Only Detection** - Monitors shielded transactions via viewing keys
- 🌉 **NEAR Swap Engine** - Cross-chain ZEC → USDC settlement
- 💰 **Price Oracle** - Real-time ZEC/USD pricing from CoinGecko
- 🎯 **Merchant POS** - Payment request generation and tracking

## Quick Start

```bash
# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev
```

Server runs at: **http://localhost:4000**

## API Endpoints

### Health Check
```bash
GET /health
```

### AI Query
```bash
POST /ai
Content-Type: application/json

{
  "query": "How much did I spend this month?"
}
```

### Add Ledger Entry
```bash
POST /ledger/add
Content-Type: application/json

{
  "amount": 0.5,
  "asset": "ZEC",
  "direction": "outgoing"
}
```

### ZEC → USDC Swap
```bash
POST /swap/zec-to-usdc
Content-Type: application/json

{
  "amount": 0.01,
  "merchantAccount": "merchant.testnet"
}
```

### Watch Incoming Payments
```bash
GET /watch/status
```

## Environment Configuration

See `.env.example` for all available options.

### Required Variables

```env
OLLAMA_MODEL=phi3:mini
LIGHTWALLETD_URL=https://lightwalletd.testnet.z.cash:9067
INCOMING_VIEW_KEY=zxviewkey...
LEDGER_DB_PASSWORD=your_secure_password
NEAR_ACCOUNT_ID=your-account.testnet
```

## Project Structure

```
backend/
├── src/
│   ├── server.ts           # Main Express server
│   ├── ai/                 # Ollama AI integration
│   ├── ledger/             # SQLCipher encrypted storage
│   ├── zcash/              # Lightwalletd client & watchers
│   ├── near/               # NEAR swap engine
│   ├── merchant/           # POS & payment tracking
│   └── utils/              # Shared utilities
├── tests/
├── .env.example
├── package.json
└── tsconfig.json
```

## Development

```bash
# Run with auto-reload
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Run tests
npm test

# Lint code
npm run lint
```

## Deployment

### Fly.io
```bash
fly launch
fly deploy
fly secrets set LEDGER_DB_PASSWORD=xxx
```

### Render
1. Connect GitHub repo
2. Build Command: `npm install && npm run build`
3. Start Command: `npm start`
4. Add environment variables in dashboard

## Troubleshooting

See [DEVELOPMENT.md](../DEVELOPMENT.md) for detailed troubleshooting guide.

## License

MIT License - see [LICENSE](../LICENSE)
