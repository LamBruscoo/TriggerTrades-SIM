"""
Main entry point for Streamlit Cloud deployment.
This starts the trading engine in the background and then runs the dashboard.
"""
import subprocess
import sys
import threading
import os, json, time, pathlib
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Ensure we're in the right directory
os.chdir(pathlib.Path(__file__).parent)

# Create runtime directory if it doesn't exist
pathlib.Path("runtime").mkdir(exist_ok=True)

# Force simulator mode for cloud deployment
os.environ["FORCE_SIM"] = "1"

# Start the trading engine in a background thread
def start_engine():
    """Start the trading engine in the background"""
    subprocess.run([sys.executable, "run_demo.py"])

# Only start the engine once using Streamlit's session state
if "engine_started" not in st.session_state:
    st.session_state.engine_started = True
    print("🚀 Starting trading engine in background...")
    engine_thread = threading.Thread(target=start_engine, daemon=True)
    engine_thread.start()
    # Give it a moment to initialize
    time.sleep(3)
    print("✅ Trading engine started successfully")

# ===== DASHBOARD CODE STARTS HERE =====

st.set_page_config(page_title="DIA Strategy Monitor", layout="wide")

RUNTIME_DIR = pathlib.Path("runtime")
STATE_PATH = RUNTIME_DIR / "state.json"
TRADES_PATH = RUNTIME_DIR / "trades.jsonl"

mode_text = "unknown"
if (RUNTIME_DIR / "mode.txt").exists():
    try:
        mode_text = (RUNTIME_DIR / "mode.txt").read_text().strip()
    except Exception:
        pass
mode_badge = f"🟢 LIVE" if mode_text.lower()=="live" else ("🟠 SIM" if mode_text.lower()=="sim" else "⚪ UNKNOWN")
st.title(f"📈 DIA Strategy Monitor {mode_badge}")

# Interactive Control Panel
st.markdown("---")
st.subheader("🎛️ Control Panel")
control_cols = st.columns(6)

with control_cols[0]:
    if st.button("🔄 RESET", help="Zero out & reset", type="primary", use_container_width=True):
        try:
            (RUNTIME_DIR / "reset.request").write_text("reset")
            time.sleep(0.3)
            st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")

with control_cols[1]:
    pause_flag = RUNTIME_DIR / "pause.flag"
    is_paused = pause_flag.exists()
    if is_paused:
        if st.button("▶️ RESUME", help="Resume trading", type="secondary", use_container_width=True):
            try:
                pause_flag.unlink(missing_ok=True)
                time.sleep(0.3)
                st.rerun()
            except Exception as e:
                st.error(f"Resume failed: {e}")
    else:
        if st.button("⏸️ PAUSE", help="Pause new signals", type="secondary", use_container_width=True):
            try:
                pause_flag.write_text("paused")
                time.sleep(0.3)
                st.rerun()
            except Exception as e:
                st.error(f"Pause failed: {e}")

with control_cols[2]:
    if st.button("🔁 SWITCH MODE", help="Toggle SIM/LIVE", use_container_width=True):
        try:
            new_mode = "live" if mode_text.lower() == "sim" else "sim"
            (RUNTIME_DIR / "mode.request").write_text(new_mode)
            time.sleep(0.3)
            st.rerun()
        except Exception as e:
            st.error(f"Mode switch failed: {e}")

with control_cols[3]:
    if st.button("📊 STATUS", help="Refresh status", use_container_width=True):
        st.rerun()

with control_cols[4]:
    if st.button("🗑️ CLEAR LOGS", help="Archive and clear trades/prices", use_container_width=True):
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_dir = RUNTIME_DIR / "archive"
            archive_dir.mkdir(exist_ok=True)
            
            # Archive existing files
            if TRADES_PATH.exists():
                TRADES_PATH.rename(archive_dir / f"trades_{timestamp}.jsonl")
            if (RUNTIME_DIR / "prices.jsonl").exists():
                (RUNTIME_DIR / "prices.jsonl").rename(archive_dir / f"prices_{timestamp}.jsonl")
            
            # Pause trading automatically when clearing logs
            pause_flag = RUNTIME_DIR / "pause.flag"
            if not pause_flag.exists():
                pause_flag.write_text("paused")
            
            time.sleep(0.3)
            st.rerun()
        except Exception as e:
            st.error(f"Clear failed: {e}")

with control_cols[5]:
    # Display current status - only show green when active
    if is_paused:
        st.markdown("**🔴 PAUSED**")
    else:
        st.markdown("**🟢 ACTIVE**")

st.markdown("---")
st.markdown("---")

left, right = st.columns([1,3])

with left:
    st.subheader("Engine Status")
    state = {}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text())
        except Exception:
            state = {}
    
    # Trading status indicator
    pause_flag = RUNTIME_DIR / "pause.flag"
    is_paused = pause_flag.exists()
    status_color = "🔴" if is_paused else "🟢"
    status_text = "PAUSED" if is_paused else "ACTIVE"
    st.markdown(f"### {status_color} {status_text}")
    
    st.metric("Phase", state.get("phase","—"))
    lp = state.get("last_price")
    st.metric("Last Price", f"{lp:.2f}" if isinstance(lp,(int,float)) else "—")
    bp = state.get("base_price")
    if isinstance(bp,(int,float)) and isinstance(lp,(int,float)):
        delta = lp - bp
        st.metric("Base Price", f"{bp:.2f}", delta=f"{delta:+.2f}")
    else:
        st.metric("Base Price", f"{bp:.2f}" if isinstance(bp,(int,float)) else "—")
    
    fop = state.get("first_order_price")
    if isinstance(fop,(int,float)) and isinstance(lp,(int,float)):
        delta_first = lp - fop
        st.metric("First Order Px", f"{fop:.2f}", delta=f"{delta_first:+.2f}")
    else:
        st.metric("First Order Px", f"{fop:.2f}" if isinstance(fop,(int,float)) else "—")
    
    cyc = state.get("cycles")
    st.metric("Cycles in Window", cyc if cyc is not None else "—")
    
    # Calculate and show position & PnL from trades
    current_position = 0
    current_pnl = 0.0
    if TRADES_PATH.exists():
        try:
            trades_df = pd.read_json(TRADES_PATH, lines=True)
            if not trades_df.empty:
                # Calculate position
                current_position = int((trades_df['qty'].where(trades_df['side']=="BUY", -trades_df['qty'])).sum())
                
                # Calculate PnL (simple realized + unrealized)
                open_position = 0
                open_vwap = 0.0
                realized_pnl = 0.0
                
                for idx in trades_df.index:
                    side = trades_df.loc[idx, 'side']
                    qty = trades_df.loc[idx, 'qty']
                    price = trades_df.loc[idx, 'price']
                    
                    if price == 0:
                        continue
                    
                    delta = qty if side == "BUY" else -qty
                    
                    # Calculate realized PnL for closing trades
                    if open_position != 0 and ((open_position > 0 and delta < 0) or (open_position < 0 and delta > 0)):
                        close_qty = min(abs(delta), abs(open_position))
                        if open_position > 0:
                            realized_pnl += (price - open_vwap) * close_qty
                        else:
                            realized_pnl += (open_vwap - price) * close_qty
                    
                    # Update position and VWAP
                    if open_position == 0 or (open_position > 0 and delta > 0) or (open_position < 0 and delta < 0):
                        new_vwap = ((abs(open_position) * open_vwap) + (abs(delta) * price)) / (abs(open_position) + abs(delta)) if (abs(open_position) + abs(delta)) > 0 else price
                        open_vwap = new_vwap
                    elif abs(delta) > abs(open_position):
                        open_vwap = price
                    
                    open_position += delta
                
                # Calculate unrealized PnL for open position
                unrealized_pnl = 0.0
                if open_position != 0 and lp and isinstance(lp, (int, float)):
                    if open_position > 0:
                        unrealized_pnl = (lp - open_vwap) * abs(open_position)
                    else:
                        unrealized_pnl = (open_vwap - lp) * abs(open_position)
                
                current_pnl = realized_pnl + unrealized_pnl
        except Exception as e:
            pass
    
    st.metric("Current Position", f"{current_position:+d} shares" if current_position != 0 else "0 shares")
    pnl_color = "normal" if current_pnl == 0 else ("inverse" if current_pnl < 0 else "off")
    st.metric("Daily P&L", f"${current_pnl:+,.2f}", delta=None if current_pnl == 0 else f"{current_pnl:+.2f}")
    
    st.caption("State updates ~1/sec from run_demo.py")
    # staleness warning
    ts = state.get("ts")
    if isinstance(ts,(int,float)):
        age = time.time() - ts
        if age > 10:
            st.warning(f"⚠️ State is stale ({int(age)}s old). Ensure run_demo.py is running.")
        elif age > 5:
            st.info(f"ℹ️ Last update {int(age)}s ago")

with right:
    st.subheader("Price (Candles)")
    prices_path = RUNTIME_DIR / "prices.jsonl"
    if prices_path.exists():
        try:
            # load last ~600 samples (~5 minutes at 2 Hz)
            with prices_path.open("r") as f:
                lines = f.readlines()[-600:]
            recs = [json.loads(x) for x in lines]
            if recs:
                pdf = pd.DataFrame(recs)
                pdf["time"] = pd.to_datetime(pdf["ts"], unit="s")
                # timeframe selector
                tf = st.selectbox("Timeframe", ["5s","15s","30s","1min"], index=2, help="Aggregate taps to OHLC")
                rule = {"5s":"5S","15s":"15S","30s":"30S","1min":"1min"}[tf]
                ohlc = (
                    pdf.set_index("time")["price"]
                    .resample(rule)
                    .agg(["first","max","min","last"])  # O H L C but adjust ordering below
                    .dropna()
                )
                ohlc.rename(columns={"first":"open","max":"high","min":"low","last":"close"}, inplace=True)
                if not ohlc.empty:
                    fig = go.Figure(data=[go.Candlestick(
                        x=ohlc.index,
                        open=ohlc["open"], high=ohlc["high"], low=ohlc["low"], close=ohlc["close"],
                        increasing_line_color="#26a69a", decreasing_line_color="#ef5350"
                    )])
                    fig.update_layout(height=250, margin=dict(l=10,r=10,t=10,b=10))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Not enough samples yet to form candles.")
            else:
                st.info("No price samples yet.")
        except Exception as ex:
            st.warning(f"Could not load prices: {ex}")
    else:
        st.info("No prices file yet. It will appear once the engine runs.")

    st.subheader("P&L Performance")
    if TRADES_PATH.exists():
        try:
            df = pd.read_json(TRADES_PATH, lines=True)
            if not df.empty:
                df['time'] = pd.to_datetime(df['ts'], unit='s')
                df = df.sort_values('time')
                
                # Calculate position and PnL
                df['pos'] = (df['qty'].where(df['side']=="BUY", -df['qty'])).cumsum()
                
                # Calculate realized + unrealized PnL per trade
                df['entry_price'] = 0.0
                df['pnl'] = 0.0
                df['unrealized_pnl'] = 0.0
                
                open_position = 0
                open_vwap = 0.0
                realized_pnl_total = 0.0
                
                for idx in df.index:
                    side = df.loc[idx, 'side']
                    qty = df.loc[idx, 'qty']
                    price = df.loc[idx, 'price']
                    
                    if price == 0:  # Skip demo orders with no price
                        df.loc[idx, 'pnl'] = 0.0
                        df.loc[idx, 'entry_price'] = 0.0
                        df.loc[idx, 'unrealized_pnl'] = 0.0
                        continue
                    
                    delta = qty if side == "BUY" else -qty
                    realized_pnl = 0.0
                    
                    # Calculate PnL for closing trades
                    if open_position != 0 and ((open_position > 0 and delta < 0) or (open_position < 0 and delta > 0)):
                        close_qty = min(abs(delta), abs(open_position))
                        if open_position > 0:  # closing long
                            realized_pnl = (price - open_vwap) * close_qty
                        else:  # closing short
                            realized_pnl = (open_vwap - price) * close_qty
                        df.loc[idx, 'pnl'] = realized_pnl
                        df.loc[idx, 'entry_price'] = open_vwap
                        realized_pnl_total += realized_pnl
                    
                    # Update open position
                    if open_position == 0 or (open_position > 0 and delta > 0) or (open_position < 0 and delta < 0):
                        # Adding to position - update VWAP
                        new_vwap = ((abs(open_position) * open_vwap) + (abs(delta) * price)) / (abs(open_position) + abs(delta)) if (abs(open_position) + abs(delta)) > 0 else price
                        open_vwap = new_vwap
                        df.loc[idx, 'entry_price'] = open_vwap  # Show VWAP for entry trades
                    elif abs(delta) > abs(open_position):
                        # Flipping position
                        open_vwap = price
                        df.loc[idx, 'entry_price'] = open_vwap
                    
                    open_position += delta
                    
                    # Calculate unrealized P&L for open position
                    if open_position != 0:
                        if open_position > 0:  # long
                            unrealized = (price - open_vwap) * abs(open_position)
                        else:  # short
                            unrealized = (open_vwap - price) * abs(open_position)
                        df.loc[idx, 'unrealized_pnl'] = unrealized
                    else:
                        df.loc[idx, 'unrealized_pnl'] = 0.0
                
                # Total PnL = realized + unrealized
                df['cumulative_pnl'] = df['pnl'].cumsum() + df['unrealized_pnl']
                
                # Per-minute PnL Chart
                df_minute = df.set_index('time')
                minute_pnl = df_minute['pnl'].resample('1min').sum().reset_index()
                minute_pnl['cumulative'] = minute_pnl['pnl'].cumsum()
                
                if len(minute_pnl) > 0:
                    fig_pnl = go.Figure()
                    
                    # Bar chart for per-minute PnL
                    colors = ['#26a69a' if x >= 0 else '#ef5350' for x in minute_pnl['pnl']]
                    fig_pnl.add_trace(go.Bar(
                        x=minute_pnl['time'],
                        y=minute_pnl['pnl'],
                        name='Per-Minute P&L',
                        marker_color=colors,
                        yaxis='y1'
                    ))
                    
                    # Line chart for cumulative PnL
                    fig_pnl.add_trace(go.Scatter(
                        x=minute_pnl['time'],
                        y=minute_pnl['cumulative'],
                        name='Cumulative P&L',
                        line=dict(color='#1f77b4', width=2),
                        yaxis='y2'
                    ))
                    
                    fig_pnl.update_layout(
                        height=220,
                        margin=dict(l=10,r=10,t=30,b=10),
                        yaxis=dict(title='Per-Minute P&L ($)', side='left'),
                        yaxis2=dict(title='Cumulative P&L ($)', side='right', overlaying='y'),
                        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                        hovermode='x unified'
                    )
                    
                    st.plotly_chart(fig_pnl, use_container_width=True)
                
                # Summary metrics
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total Trades", len(df))
                c2.metric("Position", int(df['pos'].iloc[-1]))
                total_pnl = df['cumulative_pnl'].iloc[-1]
                c3.metric("Total P&L", f"${total_pnl:,.2f}")
                # Win rate based on closed trades only (pnl != 0)
                closed_trades = df[df['pnl'] != 0]
                if len(closed_trades) > 0:
                    winning = len(closed_trades[closed_trades['pnl'] > 0])
                    c4.metric("Win Rate", f"{(winning/len(closed_trades)*100):.1f}%")
                else:
                    c4.metric("Win Rate", "N/A (no closes)")
                # Add max drawdown to summary
                running_max = df['cumulative_pnl'].cummax()
                drawdown = df['cumulative_pnl'] - running_max
                max_dd = drawdown.min()
                c5.metric("Max DD", f"${max_dd:,.0f}")
                
                # Advanced Analytics (collapsible)
                with st.expander("📊 Advanced Analytics", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Drawdown Chart
                        st.markdown("**Drawdown**")
                        fig_dd = go.Figure()
                        fig_dd.add_trace(go.Scatter(
                            x=df['time'],
                            y=drawdown,
                            fill='tozeroy',
                            fillcolor='rgba(239, 83, 80, 0.3)',
                            line=dict(color='#ef5350', width=1),
                            name='Drawdown'
                        ))
                        fig_dd.update_layout(
                            height=180,
                            margin=dict(l=10,r=10,t=10,b=10),
                            yaxis=dict(title='Drawdown ($)'),
                            showlegend=False
                        )
                        st.plotly_chart(fig_dd, use_container_width=True)
                    
                    with col2:
                        # Daily P&L
                        st.markdown("**Daily P&L**")
                        daily_pnl = df.set_index('time')['pnl'].resample('1D').sum().reset_index()
                        daily_pnl['date'] = daily_pnl['time'].dt.strftime('%Y-%m-%d')
                        
                        fig_daily = go.Figure()
                        colors_daily = ['#26a69a' if x >= 0 else '#ef5350' for x in daily_pnl['pnl']]
                        fig_daily.add_trace(go.Bar(
                            x=daily_pnl['date'],
                            y=daily_pnl['pnl'],
                            marker_color=colors_daily,
                            name='Daily P&L'
                        ))
                        fig_daily.update_layout(
                            height=180,
                            margin=dict(l=10,r=10,t=10,b=10),
                            yaxis=dict(title='Daily P&L ($)'),
                            showlegend=False
                        )
                        st.plotly_chart(fig_daily, use_container_width=True)
                        
                        # Sharpe Ratio (if enough data)
                        if len(daily_pnl) > 1:
                            daily_returns = daily_pnl['pnl']
                            sharpe = (daily_returns.mean() / daily_returns.std() * (252 ** 0.5)) if daily_returns.std() > 0 else 0
                            st.caption(f"Sharpe Ratio (annualized): {sharpe:.2f}")
                        else:
                            st.caption("Sharpe Ratio: Insufficient data")
                
                # Executions table with PnL (compact view - last 12 trades)
                st.subheader("Recent Executions")
                display_df = df[['time','side','qty','price','entry_price','pnl','unrealized_pnl','pos','reason']].tail(12).copy()
                display_df['price'] = display_df['price'].apply(lambda x: f"${x:.2f}" if x > 0 else "—")
                display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"${x:.2f}" if x > 0 else "—")
                # Show realized PnL if closed, otherwise show unrealized
                display_df['pnl_display'] = display_df.apply(
                    lambda row: f"${row['pnl']:,.2f}" if row['pnl'] != 0 else (f"${row['unrealized_pnl']:,.2f} U" if row['unrealized_pnl'] != 0 else "—"),
                    axis=1
                )
                display_df = display_df[['time','side','qty','price','entry_price','pnl_display','pos','reason']]
                display_df.columns = ['Time', 'Side', 'Qty', 'Fill Price', 'Entry Price', 'P&L', 'Position', 'Trigger']
                st.dataframe(display_df, use_container_width=True, hide_index=True, height=280)
            else:
                st.info("No executions yet.")
        except Exception as e:
            st.warning(f"Could not parse trades log: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.info("No trades yet. Waiting for triggers...")

st.caption("Auto-refreshing ...")
time.sleep(2)
st.rerun()