# 🚀 Streamlit Cloud Deployment Guide

## What I've Set Up For You

✅ Added `streamlit` to `requirements.txt`
✅ Created `.streamlit/config.toml` with optimal settings
✅ Created `streamlit_app.py` as the entry point (auto-starts trading engine)
✅ Your `.gitignore` is already configured

## Step-by-Step Deployment

### Step 1: Move Project to Main Drive (Important!)

Since you're on a flash drive (`/Volumes/DOOMFLASK`), you need to copy this to your main drive first:

```bash
# Copy project to your home directory
cp -r "/Volumes/DOOMFLASK/TriggerTrades-SIM-main" ~/TriggerTrades-SIM
cd ~/TriggerTrades-SIM
```

### Step 2: Initialize Git Repository

```bash
# Initialize git
git init

# Add all files
git add .

# Make your first commit
git commit -m "Initial commit: Trading system ready for cloud"
```

### Step 3: Create GitHub Repository

**Option A: Using GitHub CLI (if you have it)**
```bash
# Install if needed
brew install gh

# Login
gh auth login

# Create repo and push
gh repo create TriggerTrades-SIM --public --source=. --push
```

**Option B: Manual Method**
1. Go to https://github.com/new
2. Repository name: `TriggerTrades-SIM`
3. Make it **Public** (required for free Streamlit Cloud)
4. Do NOT initialize with README (you already have files)
5. Click "Create repository"

Then run:
```bash
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/TriggerTrades-SIM.git
git branch -M main
git push -u origin main
```

### Step 4: Deploy to Streamlit Cloud

1. **Go to**: https://share.streamlit.io/
2. **Sign in** with your GitHub account
3. Click **"New app"**
4. Fill in:
   - **Repository**: `YOUR_USERNAME/TriggerTrades-SIM`
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py` (this auto-starts everything!)
   - **App URL**: Choose a custom subdomain (e.g., `my-trading-demo`)
5. Click **"Deploy"**

### Step 5: Wait for Deployment (2-3 minutes)

You'll see:
- ☁️ Building...
- 📦 Installing dependencies...
- 🚀 Starting app...
- ✅ Your app is live!

### Step 6: Access Your Live Dashboard

Your app will be at: `https://YOUR-SUBDOMAIN.streamlit.app`

Example: `https://my-trading-demo.streamlit.app`

## What Will Happen

When someone visits your URL:
1. `streamlit_app.py` automatically starts `run_demo.py` in the background
2. Trading engine begins generating simulated trades
3. Dashboard loads showing real-time data
4. Everything updates live every 2 seconds!

## Features That Will Work

✅ Real-time price chart
✅ Live P&L tracking
✅ Execution table with all trades
✅ Analytics and drawdown charts
✅ All 16 triggers firing
✅ 37-second protection cycle

## Important Notes

### ⚠️ Always in Simulator Mode
- Cloud deployment automatically sets `FORCE_SIM=1`
- No real trading will occur
- No API keys needed

### 🔄 App Sleeps After Inactivity
- Free tier sleeps after ~5-7 days of no visitors
- Wakes up automatically when someone visits (takes ~30 seconds)

### 📊 Fresh Data on Each Wake
- State resets when app sleeps/wakes
- This is normal for cloud deployments

### 🔐 Making it Private (Optional)
If you upgrade to a paid plan, you can:
- Add password protection
- Restrict access to specific emails
- Use custom domain

## Sharing Your App

Once deployed, just share the URL:
```
https://YOUR-SUBDOMAIN.streamlit.app
```

**Pro tip**: Add a nice README.md to your GitHub repo with:
- Screenshot of the dashboard
- Brief description of your strategy
- Link to the live demo

## Updating Your App

After making changes locally:
```bash
cd ~/TriggerTrades-SIM
git add .
git commit -m "Updated strategy parameters"
git push
```

Streamlit Cloud auto-deploys within 1-2 minutes! 🚀

## Troubleshooting

### "App is taking too long to load"
- First load takes 2-3 minutes (installing dependencies)
- Refresh after a moment

### "Module not found" errors
- Check that all imports are in `requirements.txt`
- Currently includes: httpx, websockets, pydantic, redis, pytz, python-dateutil, plotly, streamlit

### Dashboard shows no data
- Wait 10-15 seconds for engine to populate `runtime/state.json`
- Data will appear once first beat completes

### Need help?
Check Streamlit Cloud logs:
1. Go to https://share.streamlit.io/
2. Click on your app
3. Click "Manage app" → "Logs"

## Cost

**100% FREE** for public apps with:
- Unlimited visitors
- 1 GB RAM
- 1 CPU
- Auto-scaling

Perfect for demos and portfolio projects!

---

## Quick Command Summary

```bash
# 1. Copy to main drive
cp -r "/Volumes/DOOMFLASK/TriggerTrades-SIM-main" ~/TriggerTrades-SIM
cd ~/TriggerTrades-SIM

# 2. Initialize git
git init
git add .
git commit -m "Initial commit: Trading system ready for cloud"

# 3. Push to GitHub (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/TriggerTrades-SIM.git
git branch -M main
git push -u origin main

# 4. Then deploy at: https://share.streamlit.io/
```

---

You're all set! 🎉 Follow these steps and you'll have a live cloud dashboard in minutes.
