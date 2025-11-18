#!/bin/bash
# Zero Out & Reset Trading Day Script
# This script triggers a complete position flatten and state reset

RUNTIME_DIR="runtime"
RESET_REQUEST="${RUNTIME_DIR}/reset.request"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ZERO OUT & RESET TRADING DAY                              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "This will:"
echo "  1. Close all open positions (flatten)"
echo "  2. Reset strategy state to IDLE"
echo "  3. Reset daily PnL to $0.00"
echo "  4. Resume trading with fresh state"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "Reset cancelled."
    exit 0
fi

# Create runtime directory if it doesn't exist
mkdir -p "$RUNTIME_DIR"

# Create reset request file
echo "reset" > "$RESET_REQUEST"

echo ""
echo "✓ Reset request submitted!"
echo "  → Watch the system logs for confirmation"
echo "  → Positions will be flattened within 1-2 seconds"
echo "  → Strategy state will reset immediately after"
echo ""
echo "To manually check status:"
echo "  tail -f runtime/trades.jsonl   # Watch for flatten order"
echo "  cat runtime/state.json         # Check current state"
echo ""
