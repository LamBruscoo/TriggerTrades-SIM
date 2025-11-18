# Quick Start: Zero Out & Reset

## 🚀 Usage

### Option 1: Shell Script (Easiest)
```bash
./reset_trading.sh
```

### Option 2: Python Script (Most Features)
```bash
# Interactive with confirmation
python reset_trading.py

# Auto-confirm
python reset_trading.py --yes

# Wait for completion
python reset_trading.py --yes --wait

# Check status only
python reset_trading.py --status
```

### Option 3: Manual File
```bash
echo "reset" > runtime/reset.request
```

## 📊 What Happens

1. **Closes all positions** → Position = 0
2. **Resets strategy** → Phase = IDLE
3. **Clears PnL** → Daily PnL = $0.00
4. **Resumes trading** → Starts looking for T1 triggers

## 🔍 Verify Reset

```bash
# Check state
cat runtime/state.json | jq '{phase, last_price, cycles}'

# Watch trades
tail -f runtime/trades.jsonl

# Check position
python reset_trading.py --status
```

## ⚙️ Configuration

Add to `.env`:
```bash
ENABLE_MANUAL_RESET=true  # Enable/disable feature
```

## 📖 Full Documentation

See `RESET_GUIDE.md` for complete details, troubleshooting, and advanced usage.

## ⚠️ Important Notes

- Works in both **SIM** and **LIVE** modes
- Flatten orders execute at **market price**
- 2-second delay between flatten and state reset
- Trading resumes **immediately** after reset
- Does NOT restart the entire system process
