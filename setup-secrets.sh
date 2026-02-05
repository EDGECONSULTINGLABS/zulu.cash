#!/bin/bash
# =============================================================================
# setup-secrets.sh — Initialize Docker secrets for Zulu
# =============================================================================
# Run this ONCE on first setup. Never commit the secrets/ directory.
#
# In production, replace file-based secrets with:
#   - Docker Swarm secrets (docker secret create ...)
#   - HashiCorp Vault
#   - AWS Secrets Manager / GCP Secret Manager
# =============================================================================

set -euo pipefail

SECRETS_DIR="./secrets"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔐 Zulu Secrets Setup"
echo "====================="
echo ""

# Create secrets directory
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Generate random key if not exists
generate_secret() {
    local name="$1"
    local file="$SECRETS_DIR/${name}.txt"
    
    if [ -f "$file" ]; then
        echo -e "${YELLOW}⚠  $name already exists — skipping${NC}"
    else
        # Generate 32-byte random key, base64 encoded
        openssl rand -base64 32 > "$file"
        chmod 600 "$file"
        echo -e "${GREEN}✅ $name generated${NC}"
    fi
}

# Create placeholder for user-provided secrets
create_placeholder() {
    local name="$1"
    local hint="$2"
    local file="$SECRETS_DIR/${name}.txt"
    
    if [ -f "$file" ]; then
        echo -e "${YELLOW}⚠  $name already exists — skipping${NC}"
    else
        echo "REPLACE_ME" > "$file"
        chmod 600 "$file"
        echo -e "${YELLOW}📝 $name — placeholder created (edit: $file)${NC}"
        echo "   Hint: $hint"
    fi
}

echo "Generating secrets..."
echo ""

# Auto-generated secrets
generate_secret "zulu_db_key"

# User-provided secrets (placeholders)
create_placeholder "hf_token" "Get from https://huggingface.co/settings/tokens"
create_placeholder "nillion_api_key" "Get from Nillion dashboard"

echo ""
echo "─────────────────────────────────────────────"
echo ""

# Verify .gitignore
if [ -f ".gitignore" ]; then
    if grep -q "secrets/" .gitignore; then
        echo -e "${GREEN}✅ secrets/ is in .gitignore${NC}"
    else
        echo "secrets/" >> .gitignore
        echo -e "${GREEN}✅ Added secrets/ to .gitignore${NC}"
    fi
else
    echo "secrets/" > .gitignore
    echo -e "${GREEN}✅ Created .gitignore with secrets/${NC}"
fi

echo ""
echo -e "${RED}⚠  NEVER commit the secrets/ directory${NC}"
echo -e "${RED}⚠  NEVER share secret files${NC}"
echo -e "${RED}⚠  ROTATE secrets regularly${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit $SECRETS_DIR/hf_token.txt with your HuggingFace token"
echo "  2. Edit $SECRETS_DIR/nillion_api_key.txt with your Nillion key"
echo "  3. Run: docker compose up -d"
echo ""
echo "🔐 Done."
