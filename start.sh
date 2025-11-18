#!/bin/bash
# start.sh - Launch trading system with dashboard

set -e

echo "🚀 Starting TriggerTrades Trading System..."

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Please install Python 3.11+"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Create runtime directory
mkdir -p runtime

# Set simulator mode
export FORCE_SIM=1

# Start the demo in background
echo "🎯 Starting trading engine..."
python run_demo.py > runtime/demo.log 2>&1 &
DEMO_PID=$!
echo "   Engine running (PID: $DEMO_PID)"

# Wait for engine to start
sleep 3

# Start dashboard
echo "📊 Starting dashboard..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Dashboard will open at: http://localhost:8501"
echo "  Press Ctrl+C to stop both services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Trap Ctrl+C to clean up both processes
trap "echo '🛑 Stopping services...'; kill $DEMO_PID 2>/dev/null; exit" INT TERM

# Run dashboard (blocks until Ctrl+C)
streamlit run dashboard.py --server.headless=true

# Cleanup on exit
kill $DEMO_PID 2>/dev/null || true
echo "✅ Services stopped"
