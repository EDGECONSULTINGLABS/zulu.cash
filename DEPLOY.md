# Deploy Zulu Agent to Cloud (DigitalOcean / Hetzner)

## Option A: DigitalOcean (Recommended)

### Step 1: Create a Droplet

1. Go to [cloud.digitalocean.com](https://cloud.digitalocean.com)
2. Click **Create → Droplets**
3. Choose:
   - **Image:** Ubuntu 24.04 LTS
   - **Plan:** Basic → $6/month (1GB RAM) or $12/month (2GB RAM)
   - **Region:** Closest to you
   - **Authentication:** SSH key (recommended) or password
4. Click **Create Droplet**
5. Copy the IP address

### Step 2: Copy files to your Droplet

From PowerShell on your local machine:
```powershell
scp -r "C:\Users\alula\Desktop\ZULU AI SYSTEMS\Dev\zulu-secure-docker" root@YOUR_DROPLET_IP:/root/
```

Or use FileZilla/WinSCP to upload the folder.

### Step 3: SSH and deploy

```bash
ssh root@YOUR_DROPLET_IP
cd /root/zulu-secure-docker
chmod +x deploy-hetzner.sh
./deploy-hetzner.sh
```

Enter your API keys when prompted:
- **Telegram Bot Token:** `YOUR_TELEGRAM_BOT_TOKEN`
- **Anthropic API Key:** `YOUR_ANTHROPIC_API_KEY`
- **Allowed Users:** `YOUR_TELEGRAM_USER_ID`

**Done!** Your bot now runs 24/7.

---

## Option B: Hetzner

### Step 1: Create a Server

1. Go to [console.hetzner.cloud](https://console.hetzner.cloud)
2. Create a new project → Add Server
3. Choose:
   - **Image:** Ubuntu 24.04
   - **Type:** CX11 (€4/month) or CX21 (€6/month)
4. Add your SSH key
5. Create & copy the IP

### Step 2: Copy files and deploy

```powershell
scp -r "C:\Users\alula\Desktop\ZULU AI SYSTEMS\Dev\zulu-secure-docker" root@YOUR_SERVER_IP:/root/
```

```bash
ssh root@YOUR_SERVER_IP
cd /root/zulu-secure-docker
chmod +x deploy-hetzner.sh
./deploy-hetzner.sh
```

---

## Manual Deploy (if script fails)

### Install Docker
```bash
curl -fsSL https://get.docker.com | sh
```

### Set environment variables
```bash
export TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
export ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"
export TELEGRAM_ALLOWED_USERS="YOUR_TELEGRAM_USER_ID"
```

### Create secrets
```bash
mkdir -p secrets
openssl rand -hex 32 > secrets/zulu_db_key.txt
echo "placeholder" > secrets/hf_token.txt
echo "placeholder" > secrets/nillion_api_key.txt
```

### Build and run
```bash
docker compose build telegram-gateway clawd-runner clawd-watchdog
docker compose up -d telegram-gateway clawd-runner clawd-watchdog
```

---

## Useful Commands

### View logs
```bash
docker logs telegram-gateway -f
```

### Check status
```bash
docker ps
```

### Restart bot
```bash
docker compose restart telegram-gateway
```

### Stop everything
```bash
docker compose down
```

### Update and redeploy
```bash
docker compose down
docker compose build --no-cache telegram-gateway
docker compose up -d telegram-gateway clawd-runner clawd-watchdog
```

---

## Minimum Server Requirements

Since you're using Claude API (not local Ollama), you only need:
- **1 vCPU**
- **1 GB RAM** (2 GB recommended)
- **10 GB disk**

The cheapest Hetzner CX11 (€4/month) is sufficient.

---

## Security Notes

- Your API keys are passed via environment variables
- The bot only responds to allowed user IDs
- Rate limiting is enabled (10 requests/minute)
- All containers run with minimal privileges
