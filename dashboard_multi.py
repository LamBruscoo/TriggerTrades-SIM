# dashboard_multi.py — Streamlit dashboard for multi-symbol monitoring
import json, glob, time, pathlib
import pandas as pd
import streamlit as st

RUNTIME = pathlib.Path("runtime")
st.set_page_config(page_title="Multi-Symbol Monitor", layout="wide")

st.title("🌍 Multi-Symbol Strategy Monitor")
st.caption("Shows per-symbol state (~1 Hz), price taps (~2 Hz), and recent executions from runtime/ files.")

# Control Panel
st.markdown("---")
st.subheader("🎛️ Control Panel")
control_cols = st.columns(5)

with control_cols[0]:
    if st.button("🔄 RESET ALL", help="Reset all symbols", type="primary", use_container_width=True):
        try:
            (RUNTIME / "reset.request").write_text("reset")
            st.success("✓ Reset triggered!")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"Reset failed: {e}")

with control_cols[1]:
    pause_flag = RUNTIME / "pause.flag"
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
            mode_file = RUNTIME / "mode.txt"
            current_mode = mode_file.read_text().strip().lower() if mode_file.exists() else "sim"
            new_mode = "live" if current_mode == "sim" else "sim"
            (RUNTIME / "mode.request").write_text(new_mode)
            time.sleep(0.3)
            st.rerun()
        except Exception as e:
            st.error(f"Mode switch failed: {e}")

with control_cols[3]:
    if st.button("📊 REFRESH", help="Manual refresh", use_container_width=True):
        st.rerun()

with control_cols[4]:
    # Display current status - only show green when active
    if is_paused:
        st.markdown("**🔴 PAUSED**")
    else:
        st.markdown("**🟢 ACTIVE**")

st.markdown("---")

with st.sidebar:
    st.header("Refresh Settings")
    interval_ms = st.slider("Refresh interval (ms)", 500, 5000, 1000, 100)
    auto = st.toggle("Auto refresh", value=True, help="Timer-based rerun (safe replacement for deprecated autorefresh).")
    if st.button("Manual refresh now"):
        st.rerun()

# timer-based rerun
if auto:
    last = st.session_state.get("last_refresh_ts", 0.0)
    now = time.time()
    if now - last >= interval_ms / 1000.0:
        st.session_state["last_refresh_ts"] = now
        # Streamlit >=1.32: st.rerun(); older: st.experimental_rerun()
        try:
            st.rerun()
        except Exception:
            try:
                st.experimental_rerun()
            except Exception:
                pass

# load per-symbol state
state_files = sorted(glob.glob(str(RUNTIME / "state_*.json")))
rows = []
for path in state_files:
    try:
        j = json.loads(pathlib.Path(path).read_text())
        rows.append({
            "symbol": j.get("symbol"),
            "last_price": j.get("last_price"),
            "phase": j.get("phase"),
            "cycles": int(j.get("cycles", 0) or 0),
            "position": int(j.get("position", 0) or 0),
            "ts": float(j.get("ts", 0.0) or 0.0),
        })
    except Exception:
        pass

if not rows:
    st.info("No state files found yet. Run the engine first: `python run_multi.py`")
    st.stop()

df = pd.DataFrame(rows).sort_values("symbol")

st.subheader("Overview")
st.dataframe(
    df[["symbol","last_price","phase","cycles","position","ts"]].rename(columns={"ts":"updated_at"}),
    hide_index=True,
    use_container_width=True
)

symbols = df["symbol"].tolist()
sel = st.selectbox("Select symbol", symbols, index=0)

left, right = st.columns([2,1], gap="large")

with left:
    st.markdown(f"### {sel} — live price trace (last ~3 minutes)")
    prices_path = RUNTIME / f"prices_{sel}.jsonl"
    ts_list, px_list = [], []
    if prices_path.exists():
        try:
            with open(prices_path, "r") as f:
                tail = f.readlines()[-360:]
            for line in tail:
                j = json.loads(line); ts_list.append(float(j["ts"])); px_list.append(float(j["price"]))
        except Exception:
            pass
    if px_list:
        chart_df = pd.DataFrame({"ts": ts_list, "price": px_list}).sort_values("ts").set_index("ts")
        st.line_chart(chart_df, height=260)
    else:
        st.warning("No prices yet for this symbol.")

with right:
    st.markdown("### Latest snapshot")
    sel_state = df[df["symbol"] == sel].iloc[0].to_dict()
    st.json({
        "last_price": sel_state.get("last_price"),
        "phase": sel_state.get("phase"),
        "cycles": int(sel_state.get("cycles", 0)),
        "position": int(sel_state.get("position", 0)),
        "updated_at": sel_state.get("ts"),
    })

    st.markdown("### Recent executions")
    trades_csv = RUNTIME / f"trades_{sel}.csv"
    if trades_csv.exists():
        try:
            tdf = pd.read_csv(trades_csv)
            if set(tdf.columns) != {"ts","side","qty","price"}:
                tdf = pd.read_csv(trades_csv, names=["ts","side","qty","price"], header=0)
        except Exception:
            tdf = pd.read_csv(trades_csv, names=["ts","side","qty","price"])
        st.dataframe(tdf.tail(25), hide_index=True, use_container_width=True)
    else:
        st.write("No trades yet.")

st.caption("US symbols via Alpaca (use quotes after-hours). Non-US stubs via simulator. Telemetry in runtime/.")
