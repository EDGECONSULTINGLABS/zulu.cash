#!/bin/bash
# Zulu Verification System - Installation Script

set -e

echo "🔐 Zulu Verification System - Installation"
echo "=========================================="
echo ""

# Check Node.js version
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ required (found: $(node -v))"
    exit 1
fi

echo "✅ Node.js $(node -v) detected"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Dependency installation failed"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Build TypeScript
echo "🔨 Building TypeScript..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo "✅ Build complete"
echo ""

# Run tests
echo "🧪 Running tests..."
npm test

if [ $? -ne 0 ]; then
    echo "⚠️  Some tests failed, but installation is complete"
    echo "Review test output above"
else
    echo "✅ All tests passed"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Review QUICKSTART.md for usage guide"
echo "  2. Run examples: node dist/examples/basic-usage.js"
echo "  3. Run benchmarks: npm run benchmark"
echo "  4. Set environment variable: export ZULU_DB_KEY='your-key'"
echo ""
echo "🔐 Ready to secure Zulu's artifact distribution!"
