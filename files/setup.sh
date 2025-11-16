#!/bin/bash

# ZULU.cash Setup Script
# This script helps you set up the ZULU development environment

set -e

echo "🛡️  ZULU.cash Setup Script"
echo "================================"
echo ""

# Check for Node.js
echo "Checking Node.js installation..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18 or higher is required. You have version $NODE_VERSION."
    exit 1
fi

echo "✅ Node.js $(node -v) detected"
echo ""

# Check for Ollama
echo "Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama is not installed."
    echo "   Install from: https://ollama.com"
    echo "   After installing, run: ollama pull phi3:mini"
else
    echo "✅ Ollama detected"
    
    # Check if Phi-3 model is installed
    if ollama list | grep -q "phi3:mini"; then
        echo "✅ Phi-3 Mini model is installed"
    else
        echo "📥 Downloading Phi-3 Mini model..."
        ollama pull phi3:mini
    fi
fi
echo ""

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
if [ -f "package.json" ]; then
    npm install
    echo "✅ Backend dependencies installed"
else
    echo "⚠️  backend/package.json not found. Skipping backend setup."
fi
cd ..
echo ""

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
if [ -f "package.json" ]; then
    npm install
    echo "✅ Frontend dependencies installed"
else
    echo "⚠️  frontend/package.json not found. Skipping frontend setup."
fi
cd ..
echo ""

# Create .env file if it doesn't exist
echo "Setting up environment variables..."
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        echo "✅ Created backend/.env from .env.example"
        echo "⚠️  Please edit backend/.env with your configuration"
    else
        cat > backend/.env << EOF
PORT=4000

ZCASH_LIGHTWALLETD_URL=https://lightwalletd.zecwallet.co
ZCASH_IVK=REPLACE_WITH_TEST_IVK

OLLAMA_MODEL=phi3:mini

NEAR_RPC_URL=https://rpc.testnet.near.org
NEAR_ACCOUNT_ID=your_near_account.testnet
NEAR_SWAP_CONTRACT=swap-contract.testnet
EOF
        echo "✅ Created backend/.env with defaults"
        echo "⚠️  Please edit backend/.env with your configuration"
    fi
else
    echo "✅ backend/.env already exists"
fi
echo ""

# Check for SQLCipher
echo "Checking SQLCipher..."
if command -v sqlcipher &> /dev/null; then
    echo "✅ SQLCipher detected"
else
    echo "⚠️  SQLCipher not found in PATH"
    echo "   Install SQLCipher for encrypted database support"
    echo "   - macOS: brew install sqlcipher"
    echo "   - Ubuntu: apt-get install sqlcipher"
fi
echo ""

echo "================================"
echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Edit backend/.env with your configuration"
echo "  2. Run backend: cd backend && npm run dev"
echo "  3. Run frontend: cd frontend && npm run dev"
echo ""
echo "For more info, see README.md"
echo "================================"
