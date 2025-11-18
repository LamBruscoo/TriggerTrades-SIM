# Zero Out & Reset Trading Day

## Overview
The **Zero Out & Reset** feature allows you to flatten all positions and start trading fresh during the day without restarting the system.

## What It Does
1. **Closes All Positions** - Sends opposing orders to flatten your current position to zero
2. **Resets Strategy State** - Returns ladder state to IDLE, clears all trigger anchors
3. **Resets Daily PnL** - Clears realized and unrealized PnL tracking
4. **Resumes Trading** - Strategy immediately begins looking for fresh T1 entry signals

## Usage

### Method 1: Shell Script (Recommended)
```bash
./reset_trading.sh
```

This interactive script will:
- Confirm your intention
- Submit the reset request
- Provide status feedback

### Method 2: Manual File Trigger
```bash
echo "reset" > runtime/reset.request
```

The `reset_watcher()` task monitors for this file and executes the reset sequence automatically.

### Method 3: Python API
```python
# From another script or dashboard
import pathlib
pathlib.Path("runtime/reset.request").write_text("reset")
```

## How It Works

### Architecture
1. **File-based trigger** - Similar to the mode.request pattern already in your system
2. **Async watcher** - `reset_watcher()` task polls every 1 second for reset.request file
3. **Sequential execution**:
   - Calls `flatten_all()` - Creates opposing order signal
   - Waits 2 seconds for execution
   - Calls `reset_state()` - Resets engine and risk gate
   - Removes request file

### Code Flow
```
runtime/reset.request created
    ↓
reset_watcher() detects file
    ↓
flatten_all() - Queue SELL/BUY signal to close position
    ↓
Signal → Risk Gate → OMS → Execution
    ↓
Wait 2 seconds
    ↓
reset_state() - Clear engine.state + risk.daily_pnl
    ↓
Delete reset.request file
    ↓
Trading resumes fresh (T1 detection starts)
```

## Monitoring

### Watch for Reset Completion
```bash
# Terminal 1: Watch main logs
tail -f <your_log_file>

# Terminal 2: Watch trades
tail -f runtime/trades.jsonl

# Terminal 3: Monitor state
watch -n 1 'cat runtime/state.json | jq'
```

### Expected Log Output
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

## Configuration

### Enable/Disable Feature
In `.env` or environment:
```bash
ENABLE_MANUAL_RESET=true   # default: enabled
```

In `config.py`:
```python
enable_manual_reset: bool = os.getenv("ENABLE_MANUAL_RESET", "true").lower() in ("1","true","yes","on")
```

## Safety Considerations

### Risk Management
- ✅ **Position is flattened** before state reset
- ✅ **PnL is preserved** in trades.jsonl before reset
- ✅ **2-second delay** ensures execution before state clear
- ⚠️ **Market risk** - Flatten orders execute at market price

### When to Use
- **Realized significant profit** - Lock in gains and start fresh
- **Hit daily loss threshold** - Reset after market conditions improve
- **Strategy state corruption** - Clear stuck ladder states
- **Testing/development** - Reset between test cycles
- **Mid-day restart** - Without restarting the entire process

### When NOT to Use
- ❌ During active T4/T5 ladder progression (wait for completion)
- ❌ In highly volatile markets (flatten orders may slip)
- ❌ If you want to preserve current ladder positioning

## Integration with Dashboard

### Add Reset Button (Example)
```python
# In dashboard.py or dashboard_multi.py
import streamlit as st

if st.button("🔄 ZERO OUT & RESET", type="primary"):
    try:
        pathlib.Path("runtime/reset.request").write_text("reset")
        st.success("✓ Reset requested! Watch logs for confirmation.")
    except Exception as e:
        st.error(f"Reset failed: {e}")
```

## Comparison with EOD Reset

| Feature | Manual Reset | EOD Auto-Reset |
|---------|--------------|----------------|
| Trigger | Manual (file/script) | Scheduled (16:00 ET) |
| Timing | Any time during day | End of trading day |
| Position | Closes immediately | Closes at EOD |
| PnL Reset | ✅ Yes | ✅ Yes |
| State Reset | ✅ Yes | ✅ Yes |
| Resumes Trading | ✅ Immediately | ❌ Next day |

## Troubleshooting

### Reset Not Executing
1. Check if feature is enabled: `cat .env | grep ENABLE_MANUAL_RESET`
2. Verify file exists: `ls -la runtime/reset.request`
3. Check logs for errors in reset_watcher()
4. Ensure system is running: `ps aux | grep run_demo`

### Position Not Flattening
1. Check current position: `cat runtime/state.json | jq .last_price`
2. Verify risk gate isn't blocking orders (throttle, max loss)
3. Check OMS mode: `cat runtime/mode.txt` (works in both live and sim)
4. Review trades.jsonl for flatten execution

### State Not Resetting
1. Confirm flatten completed: `tail -5 runtime/trades.jsonl`
2. Check if reset_state() was called: Look for "[RESET]" log
3. Verify state.json shows phase="IDLE": `cat runtime/state.json | jq .phase`

## Advanced: Scheduled Resets

### Reset at Multiple Times Per Day
```python
# Add to run_demo.py
async def scheduled_reset_watcher():
    """Reset at specific times: 12:00 PM and 2:00 PM ET"""
    import datetime as dt
    from zoneinfo import ZoneInfo
    
    reset_times = ["12:00", "14:00"]  # 24-hour format
    
    while True:
        now = dt.datetime.now(ZoneInfo("America/New_York"))
        current_time = now.strftime("%H:%M")
        
        if current_time in reset_times:
            print(f"[SCHEDULED-RESET] Triggering reset at {current_time}")
            pathlib.Path("runtime/reset.request").write_text("reset")
            # Wait until next minute to avoid re-triggering
            await asyncio.sleep(60)
        else:
            await asyncio.sleep(30)  # Check every 30 seconds

# Add to tasks list:
# asyncio.create_task(scheduled_reset_watcher()),
```

## Files Modified

1. **config.py** - Added `enable_manual_reset` setting
2. **risk_gate.py** - Added `reset_daily_pnl()` method
3. **run_demo.py** - Enhanced `flatten_all()`, `reset_state()`, added `reset_watcher()`
4. **reset_trading.sh** - New interactive shell script
5. **RESET_GUIDE.md** - This documentation

## See Also
- `PROTECTION_CYCLE.md` - Automatic stop loss and take profit
- `eod.py` - End of day automatic reset
- `PROFITABILITY_GUIDE.md` - Strategy optimization
