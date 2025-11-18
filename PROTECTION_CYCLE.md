# 37-Second Protection Cycle

## Overview
The protection cycle is a separate 37-second beat loop that monitors open positions and exits them when the market moves adversely beyond a defined threshold. It runs independently from the 14-second entry trigger cycle.

## Implementation

### Architecture
- **Location**: `strategy_engine.py` - `protection_cycle()` async coroutine
- **Execution**: Runs via `asyncio.gather()` alongside `tick_listener()` and `beat_loop()`
- **Frequency**: Every 37 seconds (`SETTINGS.alt_beat_sec`)

### Protection Logic

#### Position Monitoring
```python
if rg.position == 0:
    continue  # No position to protect
```

#### Adverse Move Calculation
For **long positions** (position > 0):
```
adverse_move = avg_entry_price - current_price
```
If price drops below entry by `per_leg_stop_pts`, exit.

For **short positions** (position < 0):
```
adverse_move = current_price - avg_entry_price
```
If price rises above entry by `per_leg_stop_pts`, exit.

#### Exit Execution
When `adverse_move >= SETTINGS.per_leg_stop_pts`:
1. Determine exit side (opposite of position)
2. Exit entire position (`exit_qty = abs(position)`)
3. Emit OrderSignal with reason="PROTECT"
4. Log: `[PROTECTION] {side} {qty} @ {price} (avg entry: {entry}, adverse: {move} pts)`

## Integration

### Strategy Engine Constructor
```python
def __init__(self, ticks_q, signals_q, symbol=None, risk_gate=None):
    self.risk_gate = risk_gate  # RiskGate reference for position tracking
```

### Run Demo Setup
```python
risk = RiskGate()
engine = StrategyEngine(ticks_q, signals_q, risk_gate=risk)
```

### RiskGate Position Tracking
- **position**: Net open shares (positive = long, negative = short)
- **_avg_price**: VWAP entry price of current position
- **_realized_pnl**: Locked-in profit/loss from closed trades
- **update_mark_to_market()**: Recalculates daily P&L including unrealized

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `alt_beat_sec` | 37 | Protection cycle frequency (seconds) |
| `per_leg_stop_pts` | 0.71 | Stop-loss threshold (points) |

## Example Scenario

### Entry
- T1 BUY 10 @ 475.00
- T2 BUY 10 @ 475.14
- T3 BUY 30 @ 475.24
- **Position**: +50 shares
- **Avg Entry**: ~475.15

### Protection Trigger
After 37 seconds, if price drops to **474.44** (0.71 points below entry):
```
adverse_move = 475.15 - 474.44 = 0.71 pts
adverse_move >= per_leg_stop_pts → EXIT
```

Protection cycle emits:
```
OrderSignal(side="SELL", qty=50, reason="PROTECT")
```

### Dashboard Log
```
[PROTECTION] SELL 50 @ 474.44 (avg entry: 475.15, adverse: 0.71 pts)
```

## Future Enhancements

### Per-Trigger Stops
Different stop thresholds for each trigger type:
- T1-T5 ladder: 0.71 pts (tight stop)
- T7 macro: 1.50 pts (wider stop)
- T8-T10 jump: 0.90 pts
- T11 slow trend: 2.00 pts (very wide)
- T12-T13 counter: 0.60 pts (tight)
- T14 violent: 0.50 pts (very tight)
- T15 low-vol: 0.40 pts (very tight)
- T16 fallback: 1.00 pts

### Multi-Layer Protection
Track each ladder reset as independent layer:
- Layer 1: T1-T5 cycle #1 (50 shares @ 475.15 avg)
- Layer 2: T1-T5 cycle #2 (50 shares @ 476.00 avg)
- Layer 3: T7 macro (5000 shares @ 474.50)

Exit layers independently when their specific stop is hit.

### Time-Based Stops
- Exit after holding for X minutes without profit
- Tighten stops as time passes
- Weekend/overnight position management

### Trailing Stops
- Lock in profits as position moves favorably
- Dynamic stop adjustment based on volatility
- Breakeven stop after threshold profit

### Partial Exits
- Exit 50% of position at first stop level
- Exit remaining 50% at second stop level
- Scale out instead of all-or-nothing

## Testing

### Unit Tests (Pending)
- [ ] Test long position adverse move detection
- [ ] Test short position adverse move detection
- [ ] Test exit signal generation
- [ ] Test zero position handling
- [ ] Test missing RiskGate reference

### Integration Tests (Pending)
- [ ] Run with simulator generating downward move
- [ ] Verify protection exit in trades.jsonl
- [ ] Check P&L calculation after protection exit
- [ ] Test protection cycle with multiple positions

### Manual Testing
```bash
# 1. Start demo with simulator
FORCE_SIM=1 python run_demo.py

# 2. Monitor for [PROTECTION] logs in console

# 3. Check dashboard execution table for reason="PROTECT"

# 4. Verify P&L chart shows loss from stop-out
```

## Logs and Monitoring

### Console Output
```
[PROTECTION] SELL 50 @ 474.44 (avg entry: 475.15, adverse: 0.71 pts)
```

### trades.jsonl
```json
{"ts": 1234567890.123, "symbol": "SPY", "side": "SELL", "qty": 50, "price": 474.44, "reason": "PROTECT"}
```

### Dashboard
- Execution table shows "PROTECT" trigger
- P&L chart reflects realized loss
- Position counter returns to 0
