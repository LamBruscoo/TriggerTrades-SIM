# Dashboard Control Panel Guide

## Overview
Your TriggerTrades dashboards now include an **interactive control panel** with one-click buttons for all trading operations.

## 🎛️ Control Panel Buttons

### Available in Both Dashboards
- `dashboard.py` - Single symbol (DIA) dashboard
- `dashboard_multi.py` - Multi-symbol dashboard

---

## 🔄 RESET Button
**Action:** Zero out all positions and reset trading state

**What it does:**
1. Closes all open positions (flatten to zero)
2. Resets strategy state to IDLE
3. Clears daily PnL tracking
4. Resumes trading immediately

**When to use:**
- Lock in profits after a good run
- Start fresh after hitting loss limits
- Clear stuck strategy states
- Begin new trading session

**Visual feedback:**
```
✓ Reset triggered!
```

---

## ⏸️ PAUSE / ▶️ RESUME Button
**Action:** Toggle between paused and active trading

### PAUSE Mode
**What it does:**
- Stops generating new trading signals
- Keeps existing positions open
- Protection cycle remains active
- Price monitoring continues

**When to use:**
- Major market events (FOMC, jobs report)
- Need time to analyze positions
- Waiting for better market conditions
- Taking a break with positions

**Visual feedback:**
```
✓ Trading paused!
Status shows: ⏸️ PAUSED
```

### RESUME Mode
**What it does:**
- Resumes signal generation
- Continues from current state
- Starts looking for trigger conditions

**When to use:**
- After analyzing during pause
- Market conditions improved
- Ready to trade again

**Visual feedback:**
```
✓ Trading resumed!
Status shows: ▶️ ACTIVE
```

---

## 🔁 SWITCH MODE Button
**Action:** Toggle between SIM (paper) and LIVE trading

**What it does:**
1. Switches data feed (simulator ↔ live market data)
2. Changes order execution (paper ↔ real broker)
3. Updates mode indicator
4. Preserves current strategy state

**When to use:**
- Test strategy in SIM before going LIVE
- Switch to SIM during volatile markets
- Troubleshoot data feed issues
- Development and testing

**Visual feedback:**
```
✓ Switching to LIVE...
or
✓ Switching to SIM...

Badge updates: 🟢 LIVE or 🟠 SIM
```

---

## 📊 STATUS / REFRESH Button
**Action:** Manually refresh dashboard data

**What it does:**
- Reloads all data from runtime files
- Updates charts and metrics
- Refreshes trade log
- Updates state information

**When to use:**
- Want immediate update (don't want to wait)
- After executing command
- Checking if command took effect

**Note:** Dashboard auto-refreshes every 2 seconds by default

---

## 🗑️ CLEAR LOGS Button
*(Available in dashboard.py only)*

**Action:** Archive and clear trade/price logs

**What it does:**
1. Creates timestamp: `YYYYMMDD_HHMMSS`
2. Moves `trades.jsonl` → `archive/trades_YYYYMMDD_HHMMSS.jsonl`
3. Moves `prices.jsonl` → `archive/prices_YYYYMMDD_HHMMSS.jsonl`
4. Charts start fresh
5. Old data preserved in archive folder

**When to use:**
- Start of new trading day
- After major strategy changes
- Charts getting too cluttered
- Want clean slate for testing

**Visual feedback:**
```
✓ Logs archived!
```

**Location:** Check `runtime/archive/` folder for archived files

---

## 🎯 Status Indicators

### Trading Status Badge
Located in right-most control column:

- **▶️ ACTIVE** - Trading is running normally
- **⏸️ PAUSED** - Trading is paused (no new signals)

### Mode Badge
Located in dashboard title:

- **🟢 LIVE** - Live market data and real orders
- **🟠 SIM** - Simulated data and paper trading
- **⚪ UNKNOWN** - Mode file not found

### Engine Status Panel
Shows real-time:
- **🟢 ACTIVE** or **🔴 PAUSED** with large indicator
- Current phase (IDLE, T1_WINDOW, T3_WINDOW, etc.)
- Last price with update indicator
- Base price with delta from current
- First order price with delta from current
- Cycle count
- Current position
- Staleness warnings if data is old

---

## 📊 Enhanced Dashboard Features

### Left Panel - Engine Status
```
Engine Status
🟢 ACTIVE              ← Live status indicator

Phase: T3_WINDOW
Last Price: $475.50
Base Price: $475.20
  ↑ +0.30              ← Delta shown

First Order Px: $475.35
  ↑ +0.15              ← Delta shown

Cycles in Window: 2
Current Position: +1000 shares

State updates ~1/sec
ℹ️ Last update 3s ago  ← Freshness indicator
```

### Right Panel - Performance
- Candlestick chart with configurable timeframes
- P&L performance chart (per-minute bars + cumulative line)
- Summary metrics (trades, position, P&L, win rate, max DD)
- Advanced analytics (expandable):
  - Drawdown chart
  - Daily P&L bar chart
  - Sharpe ratio
- Recent executions table

---

## 💡 Workflow Examples

### Example 1: Profitable Session → Lock In
```
1. Check dashboard - see +$2,500 profit
2. Click [🔄 RESET] button
3. Wait for "✓ Reset triggered!"
4. Dashboard shows:
   - Position: 0
   - Fresh charts
   - Status: ACTIVE
5. Trading resumes automatically
```

### Example 2: Pause Before News
```
1. FOMC announcement at 2:00 PM
2. Click [⏸️ PAUSE] at 1:58 PM
3. Status shows: ⏸️ PAUSED
4. Monitor position during announcement
5. At 2:15 PM, click [▶️ RESUME]
6. Status shows: ▶️ ACTIVE
7. Trading continues
```

### Example 3: Test Then Go Live
```
1. Start in SIM mode (🟠 SIM badge)
2. Test for 30 minutes
3. Click [📊 REFRESH] to see results
4. Happy with performance
5. Click [🔁 SWITCH MODE]
6. Badge changes to: 🟢 LIVE
7. Now trading with real orders
```

### Example 4: Clean Start of Day
```
1. Previous day's trades still showing
2. Click [🗑️ CLEAR LOGS]
3. See "✓ Logs archived!"
4. Charts reset to empty
5. Check runtime/archive/ - old data saved
6. Fresh dashboard for new day
```

### Example 5: Stuck Strategy Recovery
```
1. Notice phase stuck in T4_WINDOW for 10 mins
2. Click [⏸️ PAUSE] to stop new signals
3. Check position: +500 shares
4. Click [🔄 RESET] to flatten and restart
5. Position → 0, Phase → IDLE
6. Status shows ▶️ ACTIVE
7. Strategy looking for new T1 entry
```

---

## 🔧 Technical Details

### How Controls Work
All buttons create files in the `runtime/` directory that the main process monitors:

| Button | File Created | Monitored By |
|--------|-------------|--------------|
| RESET | `runtime/reset.request` | `reset_watcher()` |
| PAUSE | `runtime/pause.flag` | `beat_loop()` |
| RESUME | Deletes `pause.flag` | `beat_loop()` |
| SWITCH MODE | `runtime/mode.request` | `mode_watcher()` |

### Response Time
- **PAUSE/RESUME**: Instant (next beat cycle, ~14 seconds max)
- **RESET**: 1-2 seconds (flatten + reset sequence)
- **MODE SWITCH**: 2-3 seconds (restart data feed)
- **CLEAR LOGS**: Instant (file operations)

### Auto-Refresh
- Default: Every 2 seconds
- Configurable in sidebar (multi-dashboard)
- Can disable and use manual refresh only

---

## 🎨 Dashboard Layout

```
╔════════════════════════════════════════════════════════════════════╗
║  📈 DIA Strategy Monitor 🟠 SIM                                    ║
╠════════════════════════════════════════════════════════════════════╣
║  🎛️ Control Panel                                                  ║
║  ┌──────────┬──────────┬──────────┬──────────┬──────────┬────────┐║
║  │🔄 RESET  │⏸️ PAUSE  │🔁 SWITCH │📊 STATUS │🗑️ CLEAR  │▶️ ACT. │║
║  │          │          │   MODE   │          │   LOGS   │        │║
║  └──────────┴──────────┴──────────┴──────────┴──────────┴────────┘║
╠════════════════════════════════════════════════════════════════════╣
║  ┌─────────────────┐  ┌──────────────────────────────────────────┐║
║  │ Engine Status   │  │ Price (Candles)                          │║
║  │ 🟢 ACTIVE       │  │ [Candlestick Chart]                      │║
║  │                 │  │                                          │║
║  │ Phase: T3       │  ├──────────────────────────────────────────┤║
║  │ Last: $475.50   │  │ P&L Performance                          │║
║  │ Base: $475.20   │  │ [Bar + Line Chart]                       │║
║  │   +0.30         │  │                                          │║
║  │                 │  │ Metrics: Trades | Pos | P&L | Win% | DD │║
║  │ Position:       │  ├──────────────────────────────────────────┤║
║  │   +1000 shares  │  │ Recent Executions                        │║
║  │                 │  │ [Table with last 12 trades]              │║
║  └─────────────────┘  └──────────────────────────────────────────┘║
╚════════════════════════════════════════════════════════════════════╝
```

---

## 🚀 Quick Start

### Start Dashboard
```bash
# Single symbol
streamlit run dashboard.py

# Multi-symbol
streamlit run dashboard_multi.py
```

### Browser Opens
Navigate to: `http://localhost:8501`

### Use Controls
Click buttons as needed - they work instantly!

---

## ⚠️ Important Notes

1. **Dashboard Must Run Alongside System**
   ```bash
   # Terminal 1
   python run_demo.py
   
   # Terminal 2
   streamlit run dashboard.py
   ```

2. **Changes Apply to Running System**
   - Dashboard controls affect the `run_demo.py` process
   - Both must be running for controls to work
   - Check logs in Terminal 1 for confirmation

3. **Multiple Dashboards OK**
   - Can run both dashboards simultaneously
   - Controls work from either dashboard
   - They both control the same system

4. **Auto-Refresh**
   - Dashboard updates every 2 seconds automatically
   - No need to manually refresh constantly
   - Use manual refresh for immediate update

---

## 📚 See Also

- `INTERACTIVE_GUIDE.md` - Terminal commands (R, P, C, S, M, Q)
- `RESET_GUIDE.md` - Complete reset documentation
- `README.md` - Main project documentation
- `run_demo.py` - Main trading system

---

**🎉 Your dashboard now has full control capabilities!**

No need to switch terminals or run separate scripts - everything is one click away!
