# Deployment Guide

## Quick Start (Local)

### Simple Method
```bash
./start.sh
```
Then open browser to `http://localhost:8501`

### Manual Method
```bash
# Terminal 1 - Trading Engine
FORCE_SIM=1 python run_demo.py

# Terminal 2 - Dashboard
streamlit run dashboard.py
```

## Docker Deployment

### Build and Run
```bash
docker-compose up --build
```
Access at `http://localhost:8501`

### Run in Background
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f
```

### Stop
```bash
docker-compose down
```

## Cloud Deployment Options

### 1. Streamlit Cloud (Free)
1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Deploy from your repo
4. **Note**: Start `run_demo.py` as background process in `~/.streamlit/config.toml`:
   ```toml
   [server]
   enableStaticServing = true
   ```

### 2. Railway.app (Free Tier)
1. Install Railway CLI: `npm i -g @railway/cli`
2. Login: `railway login`
3. Deploy: `railway up`
4. Railway will detect Dockerfile and deploy automatically

### 3. Render.com (Free)
1. Push to GitHub
2. Create new "Web Service" on Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `python run_demo.py & streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0`

### 4. DigitalOcean App Platform ($5/month)
1. Connect GitHub repo
2. Set run command: `python run_demo.py & streamlit run dashboard.py --server.port=8080 --server.address=0.0.0.0`
3. Set HTTP port: 8501

### 5. AWS EC2 / Google Cloud VM
```bash
# SSH into server
ssh user@your-server-ip

# Clone repo
git clone https://github.com/yourusername/TriggerTrades-SIM.git
cd TriggerTrades-SIM

# Run with start script
./start.sh

# Or use screen/tmux for persistent session
screen -S trading
./start.sh
# Press Ctrl+A then D to detach
```

## Sharing Access

### Option A: Port Forwarding (Local Network)
1. Get your local IP: `ifconfig | grep inet`
2. Forward port 8501 on your router
3. Share: `http://YOUR_IP:8501`

### Option B: ngrok (Internet Tunnel)
```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com

# Start trading system
./start.sh

# In another terminal, create tunnel
ngrok http 8501
```
Share the ngrok URL (e.g., `https://abc123.ngrok.io`)

### Option C: Tailscale (Secure P2P)
```bash
# Install Tailscale on both machines
# https://tailscale.com/download

# Start trading system
./start.sh

# Share your Tailscale IP
# Friend accesses: http://100.x.x.x:8501
```

## Environment Variables

Create `.env` file for configuration:
```env
FORCE_SIM=1
SYMBOL=SPY
BEAT_SEC=14
ALT_BEAT_SEC=37
SIM_BASE_PRICE=476.50
SIM_AMP=0.50
SIM_NOISE=0.05

# For live trading (optional)
ALPACA_KEY=your_key_here
ALPACA_SECRET=your_secret_here
```

## Requirements for Recipients

### Minimal Setup
```bash
# Install Python 3.11+
# Install dependencies
pip install -r requirements.txt

# Run
./start.sh
```

### Dependencies
- Python 3.11+
- See `requirements.txt` for packages

### System Requirements
- **RAM**: 256MB minimum
- **CPU**: 1 core minimum
- **Disk**: 100MB for code + logs
- **Network**: For cloud deployment only

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8501
lsof -i :8501

# Kill process
kill -9 <PID>
```

### Dashboard Won't Connect to Engine
- Check `runtime/state.json` is being updated
- Ensure `run_demo.py` is running
- Check logs: `tail -f runtime/demo.log`

### Docker Issues
```bash
# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```
