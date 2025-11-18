# Interactive Control Panel - Quick Guide

## Overview
The interactive control panel allows you to control your TriggerTrades system in real-time without stopping the process.

## Enabling Interactive Mode

### Default: ENABLED
The interactive mode is enabled by default when you run:
```bash
python run_demo.py
```

### Disable if Needed
If you want to disable it (for running in background/production):
```bash
export ENABLE_INTERACTIVE=false
python run_demo.py
```

Or add to `.env`:
```bash
ENABLE_INTERACTIVE=false
```

## Available Commands

When you start `run_demo.py`, you'll see the control panel:

```
======================================================================
  TRIGGERTRADES INTERACTIVE CONTROL PANEL
======================================================================

Commands:
  [R] Reset     → Zero out positions and reset trading state
  [P] Pause     → Pause trading (stop generating signals)
  [C] Continue  → Resume trading
  [S] Status    → Show current status
  [M] Mode      → Switch between SIM/LIVE
  [Q] Quit      → Exit the system
======================================================================

> Enter command:
```

## Command Reference

### [R] Reset - Zero Out & Fresh Start
```
> R
[CMD] Triggering RESET (zero out & restart)...
[CMD] ✓ Reset request submitted. Watch logs for confirmation.
```
**What it does:**
- Closes all positions (flatten to zero)
- Resets strategy state to IDLE
- Clears daily PnL tracking
- Resumes trading immediately

**When to use:**
- Lock in profits after a good run
- Start fresh after hitting a loss threshold
- Clear stuck ladder states
- Begin new trading session mid-day

---

### [P] Pause - Stop Trading
```
> P
[CMD] PAUSING trading...
[CMD] ✓ Trading paused. No new signals will be generated.
[CMD]   (Existing positions remain open)
```
**What it does:**
- Stops generating new trading signals
- Keeps existing positions open
- Continues monitoring prices
- Protection cycle still active

**When to use:**
- Major market event (wait and see)
- Need to analyze current positions
- Adjusting strategy parameters
- Taking a break but keeping positions

---

### [C] Continue - Resume Trading
```
> C
[CMD] RESUMING trading...
[CMD] ✓ Trading resumed. Looking for signals...
```
**What it does:**
- Resumes signal generation
- Continues from current state
- Starts looking for trigger conditions

**When to use:**
- After pausing to analyze
- Market conditions improved
- Ready to trade again

---

### [S] Status - Show Current State
```
> S
======================================================================
  CURRENT STATUS
======================================================================
Phase:        T3_WINDOW
Mode:         SIM
Last Price:   $475.50
Base Price:   $475.20
Cycles:       2

Position:     +1000 shares
Daily PnL:    +$125.50
Trading:      ACTIVE
======================================================================
```
**What it shows:**
- Current strategy phase
- Trading mode (SIM/LIVE)
- Price information
- Current position
- Daily profit/loss
- Trading status (active/paused)

**When to use:**
- Quick status check
- Verify current state
- Check position and PnL
- Confirm pause/resume worked

---

### [M] Mode - Switch SIM/LIVE
```
> M
[CMD] Current mode: SIM
Switch to (sim/live): live
[CMD] Switching to LIVE...
[CMD] ✓ Mode switch requested.
```
**What it does:**
- Switches between paper (SIM) and live trading
- Restarts tick stream
- Updates OMS mode
- Preserves current state

**When to use:**
- Testing in SIM before going LIVE
- Switching back to SIM during volatile markets
- Troubleshooting feed issues

---

### [Q] Quit - Safe Shutdown
```
> Q
[CMD] Shutting down system...
[CMD] Flattening positions before exit...
[CMD] ✓ Goodbye!
```
**What it does:**
- Flattens all positions
- Waits for execution
- Cleanly shuts down system

**When to use:**
- End of trading day
- Need to restart system
- Emergency shutdown

**⚠️ Note:** This is safer than Ctrl+C as it closes positions first.

---

## Usage Examples

### Example 1: Lock in Profits
```bash
# System made $2,000 profit
> S              # Check status
Position:     +5000 shares
Daily PnL:    +$2000.00

> R              # Reset to lock in gains
[CMD] ✓ Reset request submitted.

# Now starting fresh with $0 PnL
```

### Example 2: Pause During News Event
```bash
# Fed announcement at 2:00 PM
> P              # Pause trading
[CMD] ✓ Trading paused.

# Wait 15 minutes for volatility to settle...

> C              # Resume
[CMD] ✓ Trading resumed.
```

### Example 3: Test in SIM First
```bash
# Start in SIM mode
> S
Mode:         SIM

# Test strategy for 30 minutes...
# Everything looks good

> M              # Switch to LIVE
Switch to (sim/live): live
[CMD] ✓ Mode switch requested.
```

### Example 4: Monitor and Adjust
```bash
# Every 5 minutes, check status
> S
Position:     +2000 shares
Daily PnL:    +$500.00

# Position getting large, pause
> P
[CMD] ✓ Trading paused.

# Analyze position...
# Decide to flatten and reset

> R
[CMD] ✓ Reset request submitted.
```

---

## Technical Details

### How Pause Works
Creates a file `runtime/pause.flag` that the strategy engine checks on each beat cycle.
- **Signals:** Stopped (no new orders)
- **Positions:** Kept open
- **Protection:** Still active (stop loss/take profit)
- **Monitoring:** Continues

### How Reset Works
Triggers the same reset mechanism as `./reset_trading.sh`:
1. Creates `runtime/reset.request` file
2. `reset_watcher()` detects it
3. Flattens positions
4. Resets state and PnL
5. Resumes trading

### Non-Blocking Input
The command interface uses async input that doesn't block other tasks:
- Trading continues while waiting for commands
- 1-second timeout on input reads
- Errors are caught and ignored

---

## Tips & Best Practices

1. **Use Status Frequently**
   ```bash
   > S    # Quick check anytime
   ```

2. **Pause Before Major Events**
   - FOMC announcements
   - Jobs reports
   - Market opens/closes

3. **Reset After Large Moves**
   - Lock in profits: Reset after +$X gain
   - Limit losses: Reset after -$Y loss

4. **Test Mode Switches**
   - Always test in SIM first
   - Switch to LIVE when confident
   - Switch back to SIM if issues

5. **Safe Exit**
   - Use `Q` instead of Ctrl+C
   - Ensures positions are closed
   - Clean shutdown

---

## Troubleshooting

### Commands Not Working?
```bash
# Check if interactive mode is enabled
cat .env | grep ENABLE_INTERACTIVE

# Should show: ENABLE_INTERACTIVE=true
```

### Input Not Appearing?
- Terminal might be buffering
- Press Enter after typing command
- Check that process is running: `ps aux | grep run_demo`

### Pause Not Stopping Trades?
- Check for pause flag: `ls runtime/pause.flag`
- If missing, trading is active
- Try pausing again: Press `P`

### Status Shows Wrong Info?
- State might be updating
- Wait 1-2 seconds and check again: `S`
- Check state file directly: `cat runtime/state.json`

---

## Keyboard Shortcuts (Future Enhancement)

Currently single-key commands require Enter. Future versions may add:
- `Ctrl+R` - Quick reset
- `Ctrl+P` - Toggle pause/resume
- `Ctrl+S` - Quick status
- Arrow keys for command history

---

## Running Without Interactive Mode

If you need to run in background or production without interactive control:

```bash
# Disable interactive mode
export ENABLE_INTERACTIVE=false
python run_demo.py &

# Use file-based controls instead
echo "reset" > runtime/reset.request        # Reset
echo "reset" > runtime/pause.flag           # Pause
rm runtime/pause.flag                       # Resume
python reset_trading.py --status            # Status
```

---

## See Also

- `RESET_GUIDE.md` - Complete reset documentation
- `RESET_QUICKSTART.md` - Quick reset reference
- `status_monitor.py` - Alternative status display
- `reset_trading.py` - Script-based reset control

---

**🎉 Happy Trading with Interactive Control!**
