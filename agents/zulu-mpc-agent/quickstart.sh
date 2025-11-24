#!/bin/bash
# Quick start script for ZULU MPC Agent

set -e

echo "🚀 ZULU MPC Agent - Quick Start"
echo "================================"
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $python_version found"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r requirements.txt > /dev/null
pip install -e . > /dev/null
echo "✓ Dependencies installed"
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.template .env
    
    # Generate encryption key
    echo "Generating database encryption key..."
    db_key=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    
    # Update .env file
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/your-64-character-hex-key-here/$db_key/" .env
    else
        # Linux
        sed -i "s/your-64-character-hex-key-here/$db_key/" .env
    fi
    
    echo "✓ .env file created with encryption key"
    echo ""
    echo "⚠️  IMPORTANT: Keep your .env file secure!"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Initialize directories
echo "Initializing directories..."
python3 cli.py init
echo ""

# Check Ollama
echo "Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama is installed"
    
    # Check if Ollama is running
    if curl -s http://localhost:11434 > /dev/null 2>&1; then
        echo "✓ Ollama is running"
        
        # Check for model
        if ollama list | grep -q "llama3.1:8b"; then
            echo "✓ Model llama3.1:8b is available"
        else
            echo "Pulling llama3.1:8b model (this may take a while)..."
            ollama pull llama3.1:8b
            echo "✓ Model downloaded"
        fi
    else
        echo "⚠️  Ollama is not running"
        echo "   Start it with: ollama serve"
    fi
else
    echo "⚠️  Ollama is not installed"
    echo "   Install from: https://ollama.ai/"
fi
echo ""

# Run health check
echo "Running health check..."
python3 cli.py health
echo ""

echo "================================"
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Ensure Ollama is running: ollama serve"
echo "2. Process a call: zulu process audio.wav --title 'My Call'"
echo "3. List sessions: zulu list"
echo "4. View documentation: cat README.md"
echo ""
echo "Need help? Check CONTRIBUTING.md or open an issue."
echo "================================"
