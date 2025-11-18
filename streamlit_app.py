"""
Main entry point for Streamlit Cloud deployment.
This starts the trading engine in the background and then runs the dashboard.
"""
import subprocess
import sys
import time
import os
from pathlib import Path

# Ensure we're in the right directory
os.chdir(Path(__file__).parent)

# Create runtime directory if it doesn't exist
Path("runtime").mkdir(exist_ok=True)

# Force simulator mode for cloud deployment
os.environ["FORCE_SIM"] = "1"

# Start the trading engine in the background
print("🚀 Starting trading engine in background...")
engine_process = subprocess.Popen(
    [sys.executable, "run_demo.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Give it a moment to initialize
time.sleep(2)

# Check if engine started successfully
if engine_process.poll() is not None:
    print("⚠️ Engine process exited immediately. Check logs.")
else:
    print("✅ Trading engine started successfully")

# Now import and run the dashboard
print("📊 Loading dashboard...")
import dashboard
