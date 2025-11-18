# 🚀 Quick Start for Recipients

This is a complete trading system with 16-trigger strategy and live dashboard.

## One-Command Start

```bash
./start.sh
```

Then open your browser to **http://localhost:8501**

## What You'll See

### Dashboard Features
- **Real-time price chart** with candlesticks
- **P&L tracking** per minute with cumulative line
- **Active triggers** firing (T1-T16)
- **Position tracking** with entry/exit prices
- **Analytics**: Drawdown, Daily P&L, Sharpe Ratio
- **Execution table** showing all trades with:
  - Fill Price
  - Entry Price  
  - P&L per trade
  - Trigger name (T1, T2, T14, PROTECT, etc.)

### Trading Strategy
- **14-second entry cycle** evaluating 16 different triggers
- **37-second protection cycle** with stop-loss monitoring
- **Simulator mode** generates realistic price movements
- **Automatic P&L** calculation with VWAP tracking

## Manual Setup (if start.sh doesn't work)

```bash
# Install dependencies
pip3 install -r requirements.txt

# Terminal 1 - Start trading engine
FORCE_SIM=1 python3 run_demo.py

# Terminal 2 - Start dashboard
streamlit run dashboard.py
```

## Using Docker Instead

```bash
docker-compose up
```

Access at **http://localhost:8501**

## Sharing Over Internet

### Option 1: ngrok (Easiest)
```bash
# Install ngrok from https://ngrok.com
ngrok http 8501
```
Share the https URL it gives you.

### Option 2: Deploy to Cloud (Free)
See `DEPLOYMENT.md` for Railway, Render, Streamlit Cloud options.

## System Requirements
- Python 3.11+
- 256MB RAM
- Any OS (macOS, Linux, Windows)

## Need Help?
Check `DEPLOYMENT.md` for detailed troubleshooting and deployment options.
