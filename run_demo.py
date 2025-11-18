import os, asyncio, json, pathlib, time, sys
from config import SETTINGS
from strategy_engine import StrategyEngine
from risk_gate import RiskGate
from oms_router import OMSRouter
from events import Execution
from eod import eod_watcher

def choose_stream_fn(mode: str):
    """Return a stream function for 'live' or 'sim'."""
    if mode == "sim":
        from sim_feed import stream_ticks as s
        return s
    # Try live adapter; if it fails (missing websockets or feed issues), fall back to simulator.
    try:
        from alpaca_adapter import stream_ticks as s
        return s
    except Exception as ex:
        print(f"[MODE] Live adapter import failed ({ex}); falling back to SIM.")
        from sim_feed import stream_ticks as s
        return s

async def price_heartbeat(engine):
    last = None
    while True:
        if engine.last_price is not None and engine.last_price != last:
            last = engine.last_price
            print(f"[HEARTBEAT] last_price={last}")
        await asyncio.sleep(1)

async def telemetry(engine, risk):
    """Print periodic status updates"""
    while True:
        # refresh mark-to-market using latest engine price
        risk.update_mark_to_market(engine.last_price)
        print(f"[STATUS] Position: {risk.position} PnL: {risk.daily_pnl:.2f}")
        await asyncio.sleep(5)

async def main():
    ticks_q = asyncio.Queue()
    signals_q = asyncio.Queue()
    approvals_q = asyncio.Queue()
    exec_q = asyncio.Queue()

    risk = RiskGate()
    engine = StrategyEngine(ticks_q, signals_q, risk_gate=risk)
    
    # Determine initial mode for OMS
    runtime = pathlib.Path("runtime"); runtime.mkdir(exist_ok=True)
    initial_mode = "sim" if os.getenv("FORCE_SIM", "0").lower() in ("1","true","yes","on") else "live"
    try:
        mtxt = (runtime / "mode.txt").read_text().strip().lower()
        if mtxt in ("live","sim"):
            initial_mode = mtxt
    except Exception:
        pass
    
    oms = OMSRouter(exec_q, engine=engine, mode=initial_mode)
    if SETTINGS.enable_gpt5_for_all_clients:
        print("[FEATURE] GPT-5 for all clients: ENABLED")
    else:
        print("[FEATURE] GPT-5 for all clients: disabled")

    async def flatten_all():
        """Flatten all positions by sending opposing orders."""
        if risk.position == 0:
            print("[FLATTEN] No position to flatten.")
            return
        
        # Determine flatten side and quantity
        flatten_side = "SELL" if risk.position > 0 else "BUY"
        flatten_qty = abs(risk.position)
        current_price = engine.last_price or 0.0
        
        print(f"[FLATTEN] Closing position: {flatten_side} {flatten_qty} @ ~{current_price:.2f}")
        
        # Create a flatten signal and send through the normal flow
        from events import OrderSignal
        flatten_signal = OrderSignal(
            ts_ns=time.time_ns(),
            symbol=SETTINGS.symbol,
            side=flatten_side,
            qty=flatten_qty,
            reason="FLATTEN",
            base_price=engine.state.base_price or current_price,
            first_order_price=engine.state.first_order_price,
            from_base_pts=None,
            from_first_pts=None
        )
        await signals_q.put(flatten_signal)
        print(f"[FLATTEN] Flatten order queued: {flatten_side} {flatten_qty}")

    def reset_state():
        """Reset strategy state and daily PnL tracking."""
        engine.reset_state()
        risk.reset_daily_pnl()
        print("[RESET] State reset to IDLE, daily PnL cleared.")

    async def exec_consumer():
        while True:
            e: Execution = await exec_q.get()
            # apply pnl/position updates in risk (very simplified here)
            risk.on_fill(e.side, e.qty, e.price)
            print(f"[EXEC] {e.side} {e.qty} @ {e.price:.2f}")
            # append to trades log (epoch seconds for dashboard)
            runtime = pathlib.Path("runtime"); runtime.mkdir(exist_ok=True)
            trade_line = {
                "ts": e.ts_ns / 1_000_000_000,
                "side": e.side,
                "qty": e.qty,
                "price": e.price,
                "symbol": e.symbol,
                "reason": e.reason,
            }
            with (runtime / "trades.jsonl").open("a") as f:
                f.write(json.dumps(trade_line) + "\n")

    async def state_dumper():
        runtime = pathlib.Path("runtime"); runtime.mkdir(exist_ok=True)
        while True:
            s = engine.state
            mode = "live"
            try:
                mtxt = (runtime / "mode.txt").read_text().strip()
                if mtxt:
                    mode = mtxt
            except Exception:
                pass
            # simple tick counter derived from engine price change count could be added; instead we track last tick time
            try:
                last_tick_age = time.time() - (engine._last_tick_ts)
            except Exception:
                last_tick_age = None
            state_obj = {
                "phase": s.phase,
                "last_price": engine.last_price,
                "base_price": s.base_price,
                "first_order_price": s.first_order_price,
                "cycles": s.cycles,
                "mode": mode,
                "last_tick_age": last_tick_age,
                "ts": time.time(),
            }
            try:
                (runtime / "state.json").write_text(json.dumps(state_obj))
            except Exception as ex:
                print("[WARN] state write failed", ex)
            await asyncio.sleep(1)

    async def price_tap():
        """Append last_price to runtime/prices.jsonl at ~2 Hz for charting/candles."""
        runtime = pathlib.Path("runtime"); runtime.mkdir(exist_ok=True)
        prices_path = runtime / "prices.jsonl"
        while True:
            if engine.last_price is not None:
                try:
                    with prices_path.open("a") as f:
                        f.write(json.dumps({"ts": time.time(), "price": engine.last_price}) + "\n")
                except Exception:
                    pass
            await asyncio.sleep(0.5)

    (runtime / "mode.txt").write_text(initial_mode)

    current_mode = initial_mode
    stream_task = None

    async def start_stream(mode: str):
        nonlocal stream_task
        if stream_task and not stream_task.done():
            stream_task.cancel()
            try:
                await asyncio.wait_for(stream_task, timeout=2.0)
            except Exception:
                pass
        fn = choose_stream_fn(mode)
        print(f"[MODE] Using {'SIMULATOR' if mode=='sim' else 'LIVE'} feed")
        stream_task = asyncio.create_task(fn(SETTINGS.symbol, ticks_q))

    async def mode_watcher():
        nonlocal current_mode
        req_path = runtime / "mode.request"
        while True:
            try:
                if req_path.exists():
                    req = req_path.read_text().strip().lower()
                    if req in ("live","sim") and req != current_mode:
                        print(f"[MODE] Switching from {current_mode} to {req}")
                        current_mode = req
                        oms.mode = current_mode  # Update OMS mode
                        (runtime / "mode.txt").write_text(current_mode)
                        await start_stream(current_mode)
                        req_path.unlink(missing_ok=True)
            except Exception as ex:
                print("[WARN] mode watcher:", ex)
            await asyncio.sleep(1)

    async def reset_watcher():
        """Watch for runtime/reset.request file to trigger zero-out and reset."""
        if not SETTINGS.enable_manual_reset:
            return
        
        reset_req_path = runtime / "reset.request"
        while True:
            try:
                if reset_req_path.exists():
                    print("[RESET-WATCHER] Reset request detected!")
                    # First flatten all positions
                    await flatten_all()
                    # Wait a moment for the flatten order to execute
                    await asyncio.sleep(2)
                    # Then reset state and PnL
                    reset_state()
                    # Clean up request file
                    reset_req_path.unlink(missing_ok=True)
                    print("[RESET-WATCHER] Zero-out and reset complete. Ready to trade fresh.")
            except Exception as ex:
                print(f"[WARN] reset watcher: {ex}")
            await asyncio.sleep(1)

    # start initial stream
    await start_stream(current_mode)

    # Tick watchdog: auto-switch to SIM if no ticks after grace period in live mode.
    async def tick_watchdog():
        grace = float(os.getenv("TICK_WATCHDOG_SEC", "20"))
        start = time.time()
        while True:
            await asyncio.sleep(2)
            if current_mode == "sim":
                return  # simulator always produces ticks; stop watchdog
            # If last_price got set, ticks arrived; stop watchdog
            if engine.last_price is not None:
                return
            if time.time() - start > grace:
                print(f"[WATCHDOG] No ticks after {grace}s in live mode; switching to SIM.")
                (runtime / "mode.request").write_text("sim")
                return

    async def command_interface():
        """Interactive command interface for controlling the system"""
        print("\n" + "="*70)
        print("  TRIGGERTRADES INTERACTIVE CONTROL PANEL")
        print("="*70)
        print("\nCommands:")
        print("  [R] Reset     → Zero out positions and reset trading state")
        print("  [P] Pause     → Pause trading (stop generating signals)")
        print("  [C] Continue  → Resume trading")
        print("  [S] Status    → Show current status")
        print("  [M] Mode      → Switch between SIM/LIVE")
        print("  [Q] Quit      → Exit the system")
        print("="*70 + "\n")
        
        # Flag to control trading pause
        trading_paused = False
        
        def read_input():
            """Read input in a non-blocking way"""
            loop = asyncio.get_event_loop()
            return loop.run_in_executor(None, sys.stdin.readline)
        
        while True:
            try:
                # Use asyncio to read stdin without blocking
                line = await asyncio.wait_for(read_input(), timeout=1.0)
                cmd = line.strip().upper()
                
                if not cmd:
                    continue
                
                if cmd == 'R':
                    print("\n[CMD] Triggering RESET (zero out & restart)...")
                    (runtime / "reset.request").write_text("reset")
                    print("[CMD] ✓ Reset request submitted. Watch logs for confirmation.")
                
                elif cmd == 'P':
                    print("\n[CMD] PAUSING trading...")
                    # Create a pause flag file
                    (runtime / "pause.flag").write_text("paused")
                    print("[CMD] ✓ Trading paused. No new signals will be generated.")
                    print("[CMD]   (Existing positions remain open)")
                
                elif cmd == 'C':
                    print("\n[CMD] RESUMING trading...")
                    # Remove pause flag
                    (runtime / "pause.flag").unlink(missing_ok=True)
                    print("[CMD] ✓ Trading resumed. Looking for signals...")
                
                elif cmd == 'S':
                    print("\n" + "="*70)
                    print("  CURRENT STATUS")
                    print("="*70)
                    state = None
                    try:
                        state = json.loads((runtime / "state.json").read_text())
                    except:
                        pass
                    
                    if state:
                        print(f"Phase:        {state.get('phase', 'UNKNOWN')}")
                        print(f"Mode:         {state.get('mode', 'unknown').upper()}")
                        print(f"Last Price:   ${state.get('last_price', 0):.2f}")
                        base = state.get('base_price')
                        if base:
                            print(f"Base Price:   ${base:.2f}")
                        print(f"Cycles:       {state.get('cycles', 0)}")
                    
                    print(f"\nPosition:     {risk.position:+d} shares")
                    print(f"Daily PnL:    ${risk.daily_pnl:+.2f}")
                    
                    paused = (runtime / "pause.flag").exists()
                    print(f"Trading:      {'PAUSED' if paused else 'ACTIVE'}")
                    print("="*70)
                
                elif cmd == 'M':
                    print(f"\n[CMD] Current mode: {current_mode.upper()}")
                    new_mode = input("Switch to (sim/live): ").strip().lower()
                    if new_mode in ("sim", "live"):
                        print(f"[CMD] Switching to {new_mode.upper()}...")
                        (runtime / "mode.request").write_text(new_mode)
                        print("[CMD] ✓ Mode switch requested.")
                    else:
                        print("[CMD] ✗ Invalid mode. Use 'sim' or 'live'.")
                
                elif cmd == 'Q':
                    print("\n[CMD] Shutting down system...")
                    print("[CMD] Flattening positions before exit...")
                    await flatten_all()
                    await asyncio.sleep(2)
                    print("[CMD] ✓ Goodbye!")
                    os._exit(0)
                
                else:
                    print(f"[CMD] ✗ Unknown command: {cmd}")
                    print("[CMD] Use: R (reset), P (pause), C (continue), S (status), M (mode), Q (quit)")
                
            except asyncio.TimeoutError:
                # No input, continue loop
                await asyncio.sleep(0.1)
            except Exception as ex:
                # Ignore input errors and continue
                await asyncio.sleep(0.5)

    # Check if interactive mode is enabled
    enable_interactive = os.getenv("ENABLE_INTERACTIVE", "true").lower() in ("1","true","yes","on")
    
    tasks = [
        asyncio.create_task(telemetry(engine, risk)),
        stream_task,
        asyncio.create_task(mode_watcher()),
        asyncio.create_task(reset_watcher()),
        asyncio.create_task(tick_watchdog()),
        asyncio.create_task(engine.run()),
        asyncio.create_task(risk.run(signals_q, approvals_q)),
        asyncio.create_task(oms.run(approvals_q)),
        asyncio.create_task(exec_consumer()),
        asyncio.create_task(state_dumper()),
        asyncio.create_task(price_tap()),
        asyncio.create_task(eod_watcher(flatten_all, reset_state)),
        asyncio.create_task(price_heartbeat(engine)),
    ]
    
    # Add interactive command interface if enabled
    if enable_interactive:
        tasks.append(asyncio.create_task(command_interface()))

    # Wait for all tasks and handle any exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"[FATAL] Task {i} crashed:", repr(r))
            raise r


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
