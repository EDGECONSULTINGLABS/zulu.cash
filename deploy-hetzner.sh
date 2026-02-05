#!/bin/bash
# =============================================================================
# Zulu Agent — Hetzner Cloud Deployment Script
# =============================================================================
# Run this on your Hetzner server to deploy the Zulu Telegram bot
#
# Prerequisites:
#   - Ubuntu 22.04 or Debian 12 server
#   - SSH access to your Hetzner server
#
# Usage:
#   1. Copy this entire zulu-secure-docker folder to your server
#   2. SSH into your server
#   3. Run: chmod +x deploy-hetzner.sh && ./deploy-hetzner.sh
# =============================================================================

set -e

echo "=============================================="
echo "Zulu Agent — Hetzner Deployment"
echo "=============================================="

# ---------------------------------------------------------------------------
# Install Docker if not present
# ---------------------------------------------------------------------------
if ! command -v docker &> /dev/null; then
    echo "[1/5] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed. You may need to log out and back in."
else
    echo "[1/5] Docker already installed ✓"
fi

# ---------------------------------------------------------------------------
# Install Docker Compose plugin if not present
# ---------------------------------------------------------------------------
if ! docker compose version &> /dev/null; then
    echo "[2/5] Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
else
    echo "[2/5] Docker Compose already installed ✓"
fi

# ---------------------------------------------------------------------------
# Create secrets directory
# ---------------------------------------------------------------------------
echo "[3/5] Setting up secrets..."
mkdir -p secrets

# Check if secrets exist
if [ ! -f secrets/zulu_db_key.txt ]; then
    openssl rand -hex 32 > secrets/zulu_db_key.txt
    echo "  Created zulu_db_key.txt"
fi

if [ ! -f secrets/hf_token.txt ]; then
    echo "placeholder" > secrets/hf_token.txt
    echo "  Created hf_token.txt (placeholder)"
fi

if [ ! -f secrets/nillion_api_key.txt ]; then
    echo "placeholder" > secrets/nillion_api_key.txt
    echo "  Created nillion_api_key.txt (placeholder)"
fi

# ---------------------------------------------------------------------------
# Prompt for API keys
# ---------------------------------------------------------------------------
echo "[4/5] Configuring environment..."

# Telegram Bot Token
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    read -p "Enter your Telegram Bot Token: " TELEGRAM_BOT_TOKEN
fi

# Anthropic API Key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    read -p "Enter your Anthropic API Key: " ANTHROPIC_API_KEY
fi

# Telegram Allowed Users
if [ -z "$TELEGRAM_ALLOWED_USERS" ]; then
    read -p "Enter allowed Telegram user IDs (comma-separated): " TELEGRAM_ALLOWED_USERS
fi

# Create .env file
cat > .env << EOF
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
TELEGRAM_ALLOWED_USERS=${TELEGRAM_ALLOWED_USERS}
EOF

echo "  Environment configured ✓"

# ---------------------------------------------------------------------------
# Build and start containers
# ---------------------------------------------------------------------------
echo "[5/5] Building and starting containers..."

# Build only the essential services (no Ollama needed since using Claude)
docker compose build telegram-gateway clawd-runner clawd-watchdog

# Start services
docker compose up -d telegram-gateway clawd-runner clawd-watchdog

echo ""
echo "=============================================="
echo "✅ Deployment Complete!"
echo "=============================================="
echo ""
echo "Your Zulu Agent is now running 24/7 on Hetzner."
echo ""
echo "Services running:"
docker ps --format "table {{.Names}}\t{{.Status}}"
echo ""
echo "To view logs:"
echo "  docker logs telegram-gateway -f"
echo ""
echo "To stop:"
echo "  docker compose down"
echo ""
echo "To update:"
echo "  git pull && docker compose up -d --build"
echo ""
