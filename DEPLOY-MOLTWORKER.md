# Deploy Zulu with MoltWorker (OpenClaw on Cloudflare)

This guide sets up **Zulu on your DigitalOcean droplet** with **MoltWorker on Cloudflare Workers** as the execution backend for complex tasks.

```
Your Droplet                         Cloudflare Edge
┌──────────────────────┐             ┌──────────────────────────┐
│ telegram-gateway     │             │ MoltWorker               │
│ clawd-runner         │──WebSocket─▶│ (OpenClaw in Sandbox)    │
│ zulu-core            │             │ + AI Gateway             │
│ nightshift_dispatcher│             │ + Browser Rendering      │
└──────────────────────┘             │ + R2 persistence         │
                                     └──────────────────────────┘
```

**Why this setup:**
- Your droplet handles Telegram, clawd (fast tasks), and Zulu governance
- Cloudflare handles complex AI agent tasks (web research, browser automation, doc synthesis)
- No second droplet needed — Cloudflare manages the container lifecycle
- ~$5/mo Cloudflare Workers plan + ~$5-15/mo compute depending on usage

---

## Step 1: Deploy MoltWorker on Cloudflare

### Prerequisites
- [Cloudflare account](https://dash.cloudflare.com)
- [Workers Paid plan](https://dash.cloudflare.com/?to=/:account/workers/plans) ($5/mo)
- [Anthropic API key](https://console.anthropic.com/) (or use Cloudflare AI Gateway)
- Node.js 18+ and npm installed locally

### Clone and deploy

```bash
# Clone MoltWorker
git clone https://github.com/cloudflare/moltworker.git
cd moltworker

# Install dependencies
npm install

# Set your Anthropic API key
npx wrangler secret put ANTHROPIC_API_KEY
# Enter: sk-ant-...

# Generate and set a gateway token (SAVE THIS — you need it for Zulu)
export MOLTBOT_GATEWAY_TOKEN=$(openssl rand -hex 32)
echo "Your gateway token: $MOLTBOT_GATEWAY_TOKEN"
echo "$MOLTBOT_GATEWAY_TOKEN" | npx wrangler secret put MOLTBOT_GATEWAY_TOKEN

# Deploy
npm run deploy
```

After deploying, note your worker URL (e.g., `https://moltworker.your-account.workers.dev`).

### Set up Cloudflare Access (required)

```bash
# Set your CF Access team domain and audience tag
npx wrangler secret put CF_ACCESS_TEAM_DOMAIN
# Enter: your-team.cloudflareaccess.com

npx wrangler secret put CF_ACCESS_AUD
# Enter: your-audience-tag (from Access > Applications)
```

### Optional: Enable Telegram on MoltWorker

If you want MoltWorker to also handle Telegram directly (in addition to Zulu's gateway):

```bash
npx wrangler secret put TELEGRAM_BOT_TOKEN
npm run deploy
```

### Optional: Enable R2 persistence

So conversations and paired devices survive container restarts:

```bash
npx wrangler secret put R2_ACCESS_KEY_ID
npx wrangler secret put R2_SECRET_ACCESS_KEY
npx wrangler secret put CF_ACCOUNT_ID
npm run deploy
```

### Optional: Reduce costs with sleep

```bash
npx wrangler secret put SANDBOX_SLEEP_AFTER
# Enter: 10m (container sleeps after 10 min idle, cold start ~1-2 min)
```

### Verify MoltWorker is running

```bash
# Should return health status
curl https://your-worker.workers.dev/sandbox-health

# Open the Control UI in browser
open "https://your-worker.workers.dev/?token=YOUR_GATEWAY_TOKEN"
```

---

## Step 2: Create a CF Access Service Token (for Zulu → MoltWorker auth)

MoltWorker is protected by Cloudflare Access. Your droplet needs a **service token** to authenticate.

1. Go to [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → Access → Service Auth
2. Click **Create Service Token**
3. Name it `zulu-droplet`
4. Copy the **Client ID** and **Client Secret**

These go in your droplet's `.env` file.

---

## Step 3: Configure Zulu on your droplet

SSH into your droplet and update the `.env` file:

```bash
ssh root@YOUR_DROPLET_IP
cd /root/zulu-secure-docker

# Edit .env
nano .env
```

Add/update these variables:

```bash
# --- Existing vars ---
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_ALLOWED_USERS=your-telegram-user-id

# --- MoltWorker backend ---
MOLTWORKER_URL=https://your-worker.workers.dev
MOLTWORKER_GATEWAY_TOKEN=the-token-you-generated-in-step-1

# --- CF Access service token (from Step 2) ---
CF_ACCESS_CLIENT_ID=your-service-token-client-id
CF_ACCESS_CLIENT_SECRET=your-service-token-client-secret
```

---

## Step 4: Deploy Zulu (without openclaw-nightshift)

Since MoltWorker replaces the local `openclaw-nightshift` container, you only need:

```bash
# Build and start (no openclaw-nightshift needed)
docker compose -f docker-compose.cloud.yml up -d --build
```

Or if using the full compose file, just skip the openclaw service:

```bash
docker compose up -d telegram-gateway clawd-runner clawd-watchdog
```

---

## Step 5: Test the integration

From your droplet:

```bash
# Test MoltWorker connectivity
curl -H "CF-Access-Client-Id: YOUR_CLIENT_ID" \
     -H "CF-Access-Client-Secret: YOUR_CLIENT_SECRET" \
     https://your-worker.workers.dev/sandbox-health

# Test via Telegram
# Send a message to your bot — complex tasks should route through MoltWorker
```

Check logs:

```bash
docker logs telegram-gateway -f
# Look for: "Using MoltWorker backend: https://your-worker.workers.dev"
```

---

## How routing works

When Zulu receives a message:

1. **Simple tasks** (fetch, ping, transform) → `clawd-runner` on your droplet (fast, local)
2. **Complex tasks** (research, analysis, reports) → `MoltWorker` on Cloudflare (full OpenClaw agent)

The routing is automatic based on `MOLTWORKER_URL` being set in `.env`. If it's empty, Zulu falls back to the local `openclaw-nightshift` container.

---

## NightShift batch jobs

The `nightshift_dispatcher.py` also uses the adapter, so batch jobs automatically route to MoltWorker:

```bash
# Add a research task
python nightshift_dispatcher.py --add \
    --type web_research \
    --prompt "Research zero-knowledge proofs for ML inference"

# Run daemon (checks every 30 min during quiet hours)
python nightshift_dispatcher.py --daemon --interval 1800
```

---

## Cost breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| DigitalOcean droplet | $6-12/mo | Runs Telegram + clawd-runner |
| Cloudflare Workers plan | $5/mo | Required for Sandbox containers |
| Cloudflare compute | $5-15/mo | Depends on usage; sleep mode reduces this |
| Anthropic API | Pay per use | ~$3/MTok input, ~$15/MTok output for Sonnet |
| **Total** | **~$16-32/mo** | For a 24/7 AI assistant with web browsing |

---

## Troubleshooting

### MoltWorker container won't start
```bash
# Check MoltWorker logs
npx wrangler tail
```

### WebSocket connection fails
- Verify `MOLTWORKER_GATEWAY_TOKEN` matches on both sides
- Check CF Access service token is valid
- Ensure the container is awake (first request after sleep takes 1-2 min)

### Tasks timeout
- Default timeout is 300s (5 min)
- Increase via `MOLTWORKER_RESPONSE_TIMEOUT` in `.env`
- Check if the Sandbox container is sleeping (`SANDBOX_SLEEP_AFTER`)

### Fallback to direct LLM
If MoltWorker is unreachable, Zulu automatically falls back to calling the Anthropic API directly for task execution (no web browsing, but still functional).
