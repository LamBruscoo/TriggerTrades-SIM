# Trading System Triggers Documentation

## Overview
This system uses two concurrent monitoring cycles:
- **14-second Entry Cycle**: Evaluates market movement and generates buy/sell signals
- **37-second Protection Cycle**: Monitors positions and exits when market moves against holdings

## Core Concepts

### Position Components
Each position consists of 3 elements:
1. **Current Market Price**: Real-time index share price
2. **Execution Price**: Actual price shares were bought/sold at
3. **Share Quantity**: Number of shares in the position

### Base Price Reset
- Every 14 seconds, the current market price becomes the new "base price"
- Calculations determine direction and magnitude of movement from this base
- Example: DJIA at 47,522.12 → 0.0003% movement = 14 points

## Entry Triggers (14-Second Cycle)

### Trigger 1: Initial Directional Entry
**Condition**: Within 4 consecutive 14-second intervals, price moves 0.00024% in one direction  
**Action**: Buy/Sell **10 shares** in the direction of movement  
**Reset**: If condition not met within 4 cycles, start new 4-cycle window  
**Purpose**: Confirms directional momentum (reduces noise/flutter)

### Trigger 2: Momentum Confirmation
**Condition**: After Trigger 1, price maintains 0.0003% or higher level over next 4 intervals  
**Action**: Buy/Sell **10 shares** in same direction  
**Note**: "Maintained" means between 0.0003% to 0.0005%+ range

### Trigger 3: Acceleration Move
**Condition**: 0.0005%+ movement from original position within 3 intervals  
**Action**: Buy/Sell **30 shares** in same direction

### Trigger 4: Strong Continuation
**Condition**: Additional 0.0002% move in same direction within next 2 cycles (from Trigger 3 price)  
**Action**: Buy/Sell **200 shares**

### Trigger 5: Maximum Position & Reset
**Condition**: Another 0.0002% move in same direction within next 3 intervals (from Trigger 4 price)  
**Action**: Buy/Sell **500 shares**  
**Total Position**: 10 + 10 + 30 + 200 + 500 = **750 shares**  
**Reset**: System reboots to Trigger 1 after this execution (starts fresh cycle)

**Note**: Every 0.00144% market movement in position's direction triggers a full system reboot, creating layered independent positions.

### Trigger 6: Documentation Placeholder
*Reserved for future expansion*

### Trigger 7: Macro Position
**Condition**: From very first order, if market moves full 0.0016% in original direction  
**Action**: Buy/Sell **5,000 shares** at next 14-second interval  
**Requirement**: Original positions not yet fully exited

### Trigger 8: Gap/Jump Detection (REVISED)
**Condition**: Single 14-second interval shows 0.00034%+ jump in either direction, maintained/widened over next 2 intervals  
**Action**: Buy/Sell **1,000 shares** in jump direction

### Trigger 9: Second Jump Continuation (REVISED)
**Condition**: Market continues with second 0.00029%+ jump within next 5 intervals  
**Action**: Buy/Sell **5,000 shares**

### Trigger 10: Post-Large-Position Extension (NEW)
**Condition**: After 5,000-share position established, market moves 0.0004% in favorable direction  
**Action**: Buy/Sell **1,000 shares**  
**Favorable**: Down if we sold 5,000; Up if we bought 5,000

### Trigger 11: Slow Trend Capture (NEW)
**Condition**: 0.0011% movement in one direction over 65 intervals (15 minutes)  
**Action**: Buy/Sell **1,000 shares**  
**Status**: Always active

### Trigger 12: Counter-Position Entry (NEW)
**Condition**: Market jumps 0.0006% against our last position in any 14-second cycle  
**Action**: Buy/Sell **400 shares** in the new market direction

### Trigger 13: Counter-Position Follow-Through (NEW)
**Condition**: Market continues 0.00018% in same direction as Trigger 12  
**Action**: Buy/Sell **200 shares**

### Trigger 14: Violent Swing Capture (NEW)
**Condition**: Any-direction swing of 0.001%+ (0.0012%, 0.0013%, etc.) in single interval  
**Action**: Buy/Sell **1,000 shares**

### Trigger 15: Low Volatility Strategy (NEW)
**Condition**: Market hasn't moved more than 0.0006% in any direction over 34 intervals (9 minutes)  
**Action**: Buy/Sell **100 shares** when price hits next 0.00024% mark in same direction

### Trigger 16: Fallback Directional (NEW)
**Condition**: No clear directionality within 11 cycles  
**Action**: Buy/Sell when market moves 0.0002% in one direction

## Protection Triggers (37-Second Cycle)

*Running concurrently and independently from 14-second entry cycle*

### Purpose
Monitor existing positions and exit when market moves adversely

### Overlap Design
- 37-second intervals overlap with 14-second intervals
- One system buys/sells; the other protects/exits
- Ensures continuous risk management

### Exit Logic
- If market moves against position by defined threshold, protection trigger fires
- Exits are based on percentage movement opposite to holdings direction
- Specific protection trigger rules to be implemented in next phase

## Implementation Notes

### Continuous Operation
1. 14-second calculations always active
2. Each 14-second interval starts with fresh price calculation
3. If market moves 0.00024% opposite direction of position within 4 intervals → Trigger 1 fires in opposite direction
4. System treats each layer of positions independently

### Position Layers
- After Trigger 5 (500 shares), system resets
- New entry wave is independent of previous positions
- Multiple position layers can exist simultaneously
- Each 0.00144% move creates new layer opportunity

### Example Scenario
```
Base: 47,522.12
T1: Move to 47,533.52 (+0.00024%) → BUY 10
T2: Hold above 47,536.76 (+0.0003%) → BUY 10  
T3: Jump to 47,545.88 (+0.0005%) → BUY 30
T4: Rise to 47,555.39 (+0.0002% more) → BUY 200
T5: Climb to 47,565.01 (+0.0002% more) → BUY 500
[RESET - Now holding 750 shares]
T1 can fire again starting fresh cycle
```

## Configuration

Current implementation uses these parameters:
- `BEAT_SEC`: 14 (primary cycle)
- `ALT_BEAT_SEC`: 37 (protection cycle - to be implemented)
- Percentage thresholds mapped to trigger names (T1-T16)
- Lot sizes per trigger defined in config

## Implementation Status

### ✅ Completed
1. **14-second entry triggers (T1-T16)** - All 16 entry triggers implemented in `beat_loop()`
   - T1-T5: Sequential ladder with phase windows
   - T7: Macro position (5000 shares from first order)
   - T8/T9: Jump detection (directional entry)
   - T10: Post-jump extension (favorable move after 5000 shares)
   - T11: Slow trend (65-beat/15-minute window)
   - T12/T13: Counter-position sequence (opposite direction)
   - T14: Violent swing (any direction, always active)
   - T15: Low volatility strategy (34-beat/9-minute range check)
   - T16: Fallback directional (after 11 beats without T1-T5)

2. **37-second protection cycle** - Implemented in `protection_cycle()` coroutine
   - Monitors actual open positions via RiskGate
   - Calculates adverse movement from VWAP entry price
   - Exits entire position when adverse move ≥ `per_leg_stop_pts`
   - Logs protection exits with entry price and adverse move
   - Runs independently from entry triggers on 37-second beat

3. **Dashboard analytics**
   - Per-minute P&L chart (bars + cumulative line)
   - Drawdown chart with fill visualization
   - Daily P&L bars
   - Sharpe ratio calculation
   - Enhanced execution table with Fill Price, Entry Price, P&L, Trigger

### ⏳ Pending
1. **Multi-layer position tracking** - Each T1-T5 ladder reset should create independent position layer
2. **Testing** - Validate all 16 triggers with simulator and live data
3. **Per-trigger protection thresholds** - Different stop-loss levels for each trigger type
4. **Advanced protection logic** - Time-based stops, trailing stops, partial exits
