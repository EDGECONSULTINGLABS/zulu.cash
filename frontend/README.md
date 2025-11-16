# ZULU Frontend

Next.js + React frontend for ZULU.cash private AI agent interface.

## Features

- 💬 **AI Chat Interface** - Natural language wallet queries
- 🛡️ **Privacy-First Design** - No tracking, no analytics, no telemetry
- 💼 **Merchant Terminal** - Payment request and QR generation
- 📊 **Transaction Dashboard** - Encrypted ledger visualization
- 🎨 **Modern UI** - Tailwind CSS + Framer Motion animations
- 📱 **Responsive** - Works on desktop, tablet, and mobile

## Quick Start

```bash
# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with backend URL

# Start development server
npm run dev
```

Frontend runs at: **http://localhost:3000**

## Environment Configuration

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:4000
NEXT_PUBLIC_ENV=local
```

For production:
```env
NEXT_PUBLIC_BACKEND_URL=https://api.zulu.cash
NEXT_PUBLIC_ENV=production
```

## Project Structure

```
frontend/
├── app/                    # Next.js 14 app directory
│   ├── page.tsx           # Homepage
│   ├── chat/              # AI chat interface
│   ├── merchant/          # Merchant POS
│   └── layout.tsx         # Root layout
├── components/
│   ├── ChatInterface.tsx  # AI chat component
│   ├── TransactionList.tsx
│   ├── MerchantPOS.tsx
│   └── ui/                # Reusable UI components
├── lib/
│   ├── api.ts             # Backend API client
│   └── utils.ts           # Utility functions
├── public/                # Static assets
└── styles/
    └── globals.css        # Global styles
```

## Development

```bash
# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint

# Format code
npm run format
```

## Key Pages

### `/` - Landing Page
Marketing homepage with feature overview.

### `/chat` - AI Chat Interface
Natural language wallet queries:
- "How much did I spend this week?"
- "Show my largest transactions"
- "What's unusual in my history?"

### `/merchant` - Merchant Terminal
Payment request generation:
- Enter USD amount
- Generate Zcash payment QR
- Monitor incoming payments

### `/dashboard` - Transaction Dashboard
Encrypted ledger visualization and analytics.

## Deployment

### Vercel (Recommended)
```bash
vercel
```

Add environment variables in Vercel dashboard.

### Netlify
```bash
netlify deploy --prod
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## API Integration

The frontend communicates with the backend via REST API:

```typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_BACKEND_URL;

export async function queryAI(question: string) {
  const response = await fetch(`${API_URL}/ai`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: question })
  });
  return response.json();
}
```

## Styling

Uses Tailwind CSS with custom Zcash-inspired color palette:

```css
--zcash-gold: #F4B728
--cyber-purple: #A855F7
--dark-bg: #0a0a0f
```

## Performance

- ⚡ Next.js 14 with App Router
- 🎯 Server-side rendering
- 📦 Code splitting
- 🖼️ Optimized images
- 🚀 Edge functions

## Accessibility

- ✅ WCAG 2.1 AA compliant
- ✅ Keyboard navigation
- ✅ Screen reader friendly
- ✅ Color contrast checked

## License

MIT License - see [LICENSE](../LICENSE)
