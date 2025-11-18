#!/bin/bash
# package.sh - Create a shareable zip of the trading system

echo "📦 Packaging TriggerTrades Trading System..."

# Create temporary directory
TEMP_DIR="TriggerTrades-Package-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$TEMP_DIR"

# Copy essential files
echo "📋 Copying files..."
cp *.py "$TEMP_DIR/" 2>/dev/null || true
cp requirements.txt "$TEMP_DIR/"
cp start.sh "$TEMP_DIR/"
cp QUICKSTART.md "$TEMP_DIR/README.md"
cp DEPLOYMENT.md "$TEMP_DIR/"
cp TRIGGERS.md "$TEMP_DIR/"
cp PROTECTION_CYCLE.md "$TEMP_DIR/"
cp Dockerfile "$TEMP_DIR/" 2>/dev/null || true
cp docker-compose.yml "$TEMP_DIR/" 2>/dev/null || true
cp .gitignore "$TEMP_DIR/" 2>/dev/null || true

# Create .env.example (without real credentials)
cat > "$TEMP_DIR/.env.example" << 'EOF'
# Trading Configuration
FORCE_SIM=1
SYMBOL=SPY
BEAT_SEC=14
ALT_BEAT_SEC=37

# Simulator Settings
SIM_BASE_PRICE=476.50
SIM_AMP=0.50
SIM_NOISE=0.05

# Live Trading (Optional - get from alpaca.markets)
# ALPACA_KEY=your_key_here
# ALPACA_SECRET=your_secret_here
# ALPACA_PAPER_BASE=https://paper-api.alpaca.markets
EOF

# Make start.sh executable
chmod +x "$TEMP_DIR/start.sh"

# Create runtime directory with .gitkeep
mkdir -p "$TEMP_DIR/runtime"
touch "$TEMP_DIR/runtime/.gitkeep"

# Create zip file
ZIP_FILE="${TEMP_DIR}.zip"
echo "🗜️  Creating zip file..."
zip -rq "$ZIP_FILE" "$TEMP_DIR"

# Cleanup
rm -rf "$TEMP_DIR"

# Get file size
SIZE=$(du -h "$ZIP_FILE" | cut -f1)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Package created successfully!"
echo ""
echo "📦 File: $ZIP_FILE"
echo "📊 Size: $SIZE"
echo ""
echo "📤 Share this file with:"
echo "   • Email attachment"
echo "   • Dropbox/Google Drive link"
echo "   • WeTransfer"
echo "   • GitHub release"
echo ""
echo "🎯 Recipient instructions:"
echo "   1. Unzip the file"
echo "   2. Run: ./start.sh"
echo "   3. Open: http://localhost:8501"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
