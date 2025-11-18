"""
Simplified version of run_demo.py for cloud deployment (no interactive stdin).
"""
import os, asyncio, json, pathlib, time
os.environ["FORCE_SIM"] = "1"
os.environ["ENABLE_INTERACTIVE"] = "0"  # Disable stdin reading

from config import SETTINGS
from strategy_engine import StrategyEngine
from risk_gate import RiskGate
from oms_router import OMSRouter
from events import Execution
from eod import eod_watcher
from sim_feed import stream_ticks

async def main():
    ticks_q = asyncio.Queue()
    signals_q = asyncio.Queue()
    approvals_q = asyncio.Queue()
    exec_q = asyncio.Queue()

    risk = RiskGate()
    engine = StrategyEngine(ticks_q, signals_q, risk_gate=risk)
    
    # Setup runtime directory
    runtime = pathlib.Path("runtime")
    runtime.mkdir(exist_ok=True)
    
    # Always use SIM mode in cloud
    oms = OMSRouter(exec_q, engine=engine, mode="sim")
    (runtime / "mode.txt").write_text("sim")
    
    print("[CLOUD] Starting in SIMULATOR mode")

    async def flatten_all():
        """Flatten all positions by sending opposing orders."""
        if risk.position == 0:
            return
        
        flatten_side = "SELL" if risk.position > 0 else "BUY"
        flatten_qty = abs(risk.position)
        current_price = engine.last_price or 0.0
        
        print(f"[FLATTEN] Closing: {flatten_side} {flatten_qty} @ ~{current_price:.2f}")
        
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

    def reset_state():
        """Reset strategy state and daily PnL tracking."""
        engine.reset_state()
        risk.reset_daily_pnl()
        print("[RESET] State reset to IDLE, daily PnL cleared.")

    async def exec_consumer():
        while True:
            e: Execution = await exec_q.get()
            risk.on_fill(e.side, e.qty, e.price)
            print(f"[EXEC] {e.side} {e.qty} @ {e.price:.2f}")
            
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
        while True:
            s = engine.state
            state_obj = {
                "phase": s.phase,
                "last_price": engine.last_price,
                "base_price": s.base_price,
                "first_order_price": s.first_order_price,
                "cycles": s.cycles,
                "mode": "sim",
                "ts": time.time(),
            }
            try:
                (runtime / "state.json").write_text(json.dumps(state_obj))
            except Exception as ex:
                print(f"[WARN] state write failed: {ex}")
            await asyncio.sleep(1)

    async def price_tap():
        """Append last_price to runtime/prices.jsonl at ~2 Hz for charting."""
        prices_path = runtime / "prices.jsonl"
        while True:
            if engine.last_price is not None:
                try:
                    with prices_path.open("a") as f:
                        f.write(json.dumps({"ts": time.time(), "price": engine.last_price}) + "\n")
                except Exception:
                    pass
            await asyncio.sleep(0.5)

    async def reset_watcher():
        """Watch for runtime/reset.request file to trigger zero-out and reset."""
        if not SETTINGS.enable_manual_reset:
            return
        
        reset_req_path = runtime / "reset.request"
        while True:
            try:
                if reset_req_path.exists():
                    print("[RESET-WATCHER] Reset request detected!")
                    await flatten_all()
                    await asyncio.sleep(2)
                    reset_state()
                    reset_req_path.unlink(missing_ok=True)
                    print("[RESET-WATCHER] Reset complete.")
            except Exception as ex:
                print(f"[WARN] reset watcher: {ex}")
            await asyncio.sleep(1)

    async def telemetry():
        """Print periodic status updates"""
        while True:
            risk.update_mark_to_market(engine.last_price)
            print(f"[STATUS] Pos: {risk.position} PnL: {risk.daily_pnl:.2f} Price: {engine.last_price}")
            await asyncio.sleep(10)

    # Start all tasks
    tasks = [
        asyncio.create_task(stream_ticks(SETTINGS.symbol, ticks_q)),
        asyncio.create_task(engine.run()),
        asyncio.create_task(risk.run(signals_q, approvals_q)),
        asyncio.create_task(oms.run(approvals_q)),
        asyncio.create_task(exec_consumer()),
        asyncio.create_task(state_dumper()),
        asyncio.create_task(price_tap()),
        asyncio.create_task(reset_watcher()),
        asyncio.create_task(eod_watcher(flatten_all, reset_state)),
        asyncio.create_task(telemetry()),
    ]

    # Wait for all tasks
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"[FATAL] Task {i} crashed:", repr(r))
            raise r


if __name__ == "__main__":
    print("[CLOUD] TriggerTrades Cloud Engine Starting...")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[CLOUD] Shutdown")
