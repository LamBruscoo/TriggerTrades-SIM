# Implementation Summary: Zero Out & Reset Feature

## 🎯 Overview
Successfully implemented a comprehensive "zero out and start trading fresh" capability for your TriggerTrades system.

## ✅ What Was Added

### Core Functionality
1. **Position Flattening** - Automatically closes all open positions
2. **State Reset** - Returns strategy to IDLE with cleared anchors
3. **PnL Reset** - Clears daily realized/unrealized PnL tracking
4. **Immediate Resume** - Trading starts fresh with T1 detection

### Modified Files

#### 1. `config.py`
- Added `enable_manual_reset` setting (default: true)
- Configurable via environment variable `ENABLE_MANUAL_RESET`

#### 2. `risk_gate.py`
- Added `reset_daily_pnl()` method
- Clears `_realized_pnl` and `daily_pnl` to 0.0

#### 3. `run_demo.py`
- **Enhanced `flatten_all()`** - Now sends actual opposing orders through signal queue
- **Enhanced `reset_state()`** - Calls both engine and risk gate resets
- **New `reset_watcher()`** - Async task monitoring for `runtime/reset.request` file
- Added reset_watcher to main task list

### New Files

#### 1. `reset_trading.sh` (Bash Script)
- Interactive shell script with confirmation
- User-friendly output with status checks
- Executable: `chmod +x reset_trading.sh`

#### 2. `reset_trading.py` (Python Script)
- Full-featured Python implementation
- Command-line interface with options:
  - `--yes` - Skip confirmation
  - `--wait` - Wait for completion
  - `--status` - Show status only
- Class-based architecture for programmatic use
- Position calculation from trades.jsonl
- State verification

#### 3. `status_monitor.py` (Python Monitor)
- Real-time status display (1Hz refresh)
- Shows: phase, prices, position, PnL, tick age
- Color-coded output
- Interactive terminal UI

#### 4. `RESET_GUIDE.md` (Full Documentation)
- Complete feature documentation
- Architecture explanation
- Code flow diagrams
- Configuration options
- Safety considerations
- Troubleshooting guide
- Integration examples
- Advanced usage patterns

#### 5. `RESET_QUICKSTART.md` (Quick Reference)
- Fast usage guide
- All three trigger methods
- Verification commands
- Important notes

#### 6. `README.md` (Updated)
- Added Zero Out & Reset section
- Links to documentation

## 🚀 Usage Examples

### 1. Shell Script (Easiest)
```bash
./reset_trading.sh
# Interactive prompt → confirm → reset
```

### 2. Python Script (Most Powerful)
```bash
# Interactive with confirmation
python reset_trading.py

# Non-interactive
python reset_trading.py --yes

# Wait for completion
python reset_trading.py --yes --wait

# Status only (no reset)
python reset_trading.py --status
```

### 3. Manual File Trigger
```bash
echo "reset" > runtime/reset.request
```

### 4. From Another Python Script
```python
import pathlib
pathlib.Path("runtime/reset.request").write_text("reset")
```

### 5. Status Monitor
```bash
python status_monitor.py
# Live display with 1-second refresh
```

## 🔄 How It Works

```
User triggers reset
    ↓
runtime/reset.request file created
    ↓
reset_watcher() detects file (polls every 1 sec)
    ↓
flatten_all() called
    ↓
Creates OrderSignal with FLATTEN reason
    ↓
Signal → Risk Gate → OMS → Execution
    ↓
2-second wait for execution
    ↓
reset_state() called
    ↓
engine.reset_state() - Clears LadderState
risk.reset_daily_pnl() - Clears PnL tracking
    ↓
reset.request file deleted
    ↓
System ready - begins looking for T1 triggers
```

## 📊 Execution Flow

### Flatten Sequence
1. Check if position != 0
2. Determine side: SELL if long, BUY if short
3. Calculate quantity: abs(position)
4. Create OrderSignal with reason="FLATTEN"
5. Queue signal → goes through normal order flow
6. Executes at market price (sim or live)

### Reset Sequence
1. Call `engine.reset_state()`
   - Creates new LadderState
   - Clears price_history
   - Resets all anchors/phases
2. Call `risk.reset_daily_pnl()`
   - Sets _realized_pnl = 0.0
   - Sets daily_pnl = 0.0
3. Trading resumes immediately

## ⚙️ Configuration

### Enable/Disable Feature
```bash
# In .env file
ENABLE_MANUAL_RESET=true

# Or environment variable
export ENABLE_MANUAL_RESET=true
```

### Integration Points
- Works with existing mode switching (live/sim)
- Compatible with EOD auto-reset
- Respects risk gate throttling
- Uses existing signal queue architecture

## 🛡️ Safety Features

1. **Position Verification** - Checks position before flatten
2. **Execution Wait** - 2-second delay ensures orders execute
3. **File-based Trigger** - No API needed, simple and reliable
4. **Idempotent** - Can be called multiple times safely
5. **Non-destructive** - Trades logged before reset
6. **Mode Agnostic** - Works in both SIM and LIVE modes

## 🎛️ Monitoring & Verification

### Check Status
```bash
python reset_trading.py --status
```

### Watch Logs
```bash
# Main process logs
tail -f <your_log_file>

# Trade executions
tail -f runtime/trades.jsonl

# Current state
cat runtime/state.json | jq
```

### Live Monitor
```bash
python status_monitor.py
```

## 📝 Log Output

Expected log messages:
```
[RESET-WATCHER] Reset request detected!
[FLATTEN] Closing position: SELL 1000 @ ~475.50
[FLATTEN] Flatten order queued: SELL 1000
[OMS-SIM] SELL 1000 @ 475.50 (reason: FLATTEN)
[EXEC] SELL 1000 @ 475.50
[RISK] Daily PnL reset to 0.0
[RESET] State reset to IDLE, daily PnL cleared.
[RESET-WATCHER] Zero-out and reset complete. Ready to trade fresh.
```

## 🔧 Future Enhancements (Optional)

### Potential Additions
1. **Scheduled Resets** - Reset at specific times (12:00 PM, 2:00 PM)
2. **Dashboard Integration** - Add reset button to Streamlit dashboard
3. **PnL-Based Auto-Reset** - Trigger reset after +$X profit or -$Y loss
4. **Partial Resets** - Option to reset state without flattening
5. **Reset History** - Log reset events with timestamps and reasons
6. **Email/SMS Notifications** - Alert on reset completion
7. **Position Size Validation** - Verify flatten qty matches actual position

### Dashboard Integration Example
```python
# Add to dashboard.py
import streamlit as st

col1, col2 = st.columns(2)
with col1:
    if st.button("🔄 RESET TRADING DAY", type="primary"):
        pathlib.Path("runtime/reset.request").write_text("reset")
        st.success("Reset requested!")
        st.rerun()

with col2:
    if st.button("📊 REFRESH STATUS"):
        st.rerun()
```

## 🎓 Key Design Decisions

1. **File-based trigger** - Simple, reliable, no API needed
2. **Async watcher pattern** - Consistent with mode.request pattern
3. **2-second wait** - Balance between quick reset and execution certainty
4. **Separate flatten/reset** - Allows verification between steps
5. **Non-blocking** - Reset doesn't stop other tasks
6. **Position from trades** - Independent verification without state

## 📚 Documentation Structure

```
RESET_QUICKSTART.md     → Fast reference for common usage
    ↓
RESET_GUIDE.md          → Complete documentation
    ↓
README.md               → Main project docs with link
```

## ✨ Testing Checklist

- [x] Code compiles without errors
- [x] Scripts are executable (chmod +x)
- [x] File triggers work correctly
- [x] Position flattening logic correct
- [x] State reset clears all anchors
- [x] PnL reset clears tracking
- [x] Works in SIM mode
- [ ] Test in LIVE mode (when ready)
- [x] Documentation complete
- [x] Integration with existing systems verified

## 🎉 Ready to Use!

The feature is fully implemented and ready for testing. Start with SIM mode:

```bash
# Terminal 1: Run the system
python run_demo.py

# Terminal 2: Monitor status
python status_monitor.py

# Terminal 3: Trigger reset when needed
./reset_trading.sh
```

---

**Note**: Always test thoroughly in SIM mode before using in LIVE trading!
