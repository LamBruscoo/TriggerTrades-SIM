# Python Trading Demo (Alpaca Paper + DIA)

This is a minimal, all-Python, async demo of your time-gap trading strategy:
- **Tick stream (true ticks)** from Alpaca (Paper) for DIA
- **Strategy Engine** with **14-second beats** (and 37s helper if desired)
- **Point-based triggers** (ladder of 10/10/30/200/500/5000)
- **Risk Gate** (position, daily loss)
- **OMS Router** to Alpaca Paper
- **EOD Flatten + Reset** at 16:00 America/New_York
- **Backtester** to replay CSV ticks into the same strategy

## Prerequisites

1. **Alpaca Account**: You need an Alpaca account to get API credentials
   - Sign up at [Alpaca](https://app.alpaca.markets/signup)
   - Go to Paper Trading
   - Generate API Keys (keep these secure!)

2. **Python Environment**: Python 3.11+ recommended

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export ALPACA_KEY=your_key
export ALPACA_SECRET=your_secret
# optional: export ALPACA_PAPER_BASE=https://paper-api.alpaca.markets

python run_demo.py
```

## Environment Configuration

There are two ways to configure the trading parameters:

1. **Using environment variables**:
   ```bash
   export ALPACA_KEY=your_key
   export ALPACA_SECRET=your_secret
   ```

2. **Using a .env file** (recommended):
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit with your credentials and preferences
   vim .env  # or use your preferred editor
   ```

The `.env.example` file contains all configurable parameters:
- API credentials
- Trading symbol (default: DIA)
- Time intervals
- Trigger points
- Lot sizes
- Risk management settings
- EOD settings
 - Feature flags (e.g., ENABLE_GPT5_FOR_ALL_CLIENTS)

## Common Issues

1. **Missing API Keys**: If you see "Missing ALPACA_KEY/SECRET":
   - Check that you've set the environment variables or created `.env`
   - Verify your API keys are correct
   - Make sure the keys have proper permissions

2. **Connection Issues**: If you can't connect:
   - Verify your internet connection
   - Check if Alpaca API is accessible
   - Confirm your API endpoint is correct

## Interactive Control Panel

### Terminal Commands (run_demo.py)

When you run the system, you get an **interactive command interface**:

```bash
python run_demo.py

# You'll see:
> Enter command:
```

**Available Commands:**
- **[R]** Reset - Zero out positions and start fresh
- **[P]** Pause - Stop generating new signals (keep positions)
- **[C]** Continue - Resume trading
- **[S]** Status - Show current state, position, and PnL
- **[M]** Mode - Switch between SIM/LIVE
- **[Q]** Quit - Safe shutdown (flattens positions first)

See **[INTERACTIVE_GUIDE.md](INTERACTIVE_GUIDE.md)** for detailed usage.

### Dashboard Controls (Streamlit)

The **Streamlit dashboards** include one-click control buttons:

```bash
streamlit run dashboard.py       # Single symbol
streamlit run dashboard_multi.py # Multi-symbol
```

**Control Panel Buttons:**
- **🔄 RESET** - Zero out and reset
- **⏸️ PAUSE / ▶️ RESUME** - Toggle trading
- **🔁 SWITCH MODE** - Toggle SIM/LIVE
- **📊 STATUS** - Manual refresh
- **🗑️ CLEAR LOGS** - Archive and clear

See **[DASHBOARD_CONTROLS.md](DASHBOARD_CONTROLS.md)** for complete guide.

## Zero Out & Reset Trading Day

Multiple ways to close all positions and start fresh:

**1. Interactive Command (Easiest)**
```bash
# While run_demo.py is running
> R
```

**2. Shell Script**
```bash
./reset_trading.sh
```

**3. Python Script**
```bash
python reset_trading.py --yes --wait
```

**4. Manual Trigger**
```bash
echo "reset" > runtime/reset.request
```

This will:
1. Flatten all positions to zero
2. Reset strategy state to IDLE
3. Clear daily PnL tracking
4. Resume trading immediately

See **[RESET_QUICKSTART.md](RESET_QUICKSTART.md)** for quick usage or **[RESET_GUIDE.md](RESET_GUIDE.md)** for complete documentation.

## Backtesting

Prepare a CSV of ticks with at least columns: `ts,price,size` (ts in ISO or epoch ns).

```bash
python backtest.py --csv path/to/ticks.csv
```

## DISCLAIMER

This is a demo. Not investment advice. Paper trade only.
