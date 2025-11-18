# run_multi.py — multi-symbol orchestrator (US via Alpaca; others via sim)
import asyncio, json, pathlib
from typing import Dict, Any

from strategy_engine import StrategyEngine
from risk_gate import RiskGate
from oms_router import OMSRouter
from events import Execution

from alpaca_adapter import stream_ticks as stream_ticks_alpaca
from sim_feed import stream_ticks as stream_ticks_sim

RUNTIME = pathlib.Path("runtime"); RUNTIME.mkdir(exist_ok=True)
CONFIG = json.loads(pathlib.Path("symbols.json").read_text())

DEFAULT_LOGIC = {
    "beat_sec_rth": 14,
    "beat_sec_ah": 5,
    "atr_window": 120,
    "k_t1": 0.25, "k_t2": 0.35, "k_t3": 0.60,
    "k_t4": 0.25, "k_t5": 0.25, "k_t7": 2.0,
    "k_jump1": 0.35, "k_jump2": 0.30
}
LOGIC = {**DEFAULT_LOGIC, **CONFIG.get("logic", {})}

def session_profile(symbol: str, venue_type: str) -> Dict[str, Any]:
    import datetime as dt, pytz
    now = dt.datetime.now(pytz.timezone("America/New_York"))
    rth = (now.weekday() < 5) and ((now.hour, now.minute) >= (9,30)) and ((now.hour, now.minute) < (16,0))
    beat = LOGIC["beat_sec_rth"] if rth else LOGIC["beat_sec_ah"]
    return {"rth": rth, "beat_sec": beat}

async def launch_symbol(sym_cfg: Dict[str, Any], venue_cfg: Dict[str, Any]):
    symbol = sym_cfg["symbol"]; venue = sym_cfg["venue"]; venue_type = venue_cfg["type"]
    print(f"[BOOT] {symbol}@{venue} ({venue_type})")

    ticks_q = asyncio.Queue()
    signals_q = asyncio.Queue()
    approvals_q = asyncio.Queue()
    exec_q = asyncio.Queue()

    risk = RiskGate()
    eng = StrategyEngine(ticks_q, signals_q, risk_gate=risk)
    eng.symbol = symbol
    eng.paused = False
    
    # Determine mode for OMS (default to sim for multi-symbol)
    mode = "sim" if venue_type in ("stub_hk", "stub_eu") else "live"
    oms = OMSRouter(exec_q, engine=eng, mode=mode)

    if "risk" in sym_cfg:
        risk.max_position   = sym_cfg["risk"].get("max_position", getattr(risk, "max_position", 0))
        risk.daily_max_loss = sym_cfg["risk"].get("daily_max_loss", getattr(risk, "daily_max_loss", 0))
    if "lots" in sym_cfg:
        eng.set_lots(*sym_cfg["lots"])

    eng.set_atr_params(
        LOGIC["atr_window"],
        LOGIC["k_t1"], LOGIC["k_t2"], LOGIC["k_t3"],
        LOGIC["k_t4"], LOGIC["k_t5"], LOGIC["k_t7"],
        LOGIC["k_jump1"], LOGIC["k_jump2"]
    )
    prof = session_profile(symbol, venue_type)
    eng.set_beat(prof["beat_sec"])

    ADAPTERS = {
        "alpaca": stream_ticks_alpaca,
        "stub_hk": stream_ticks_sim,
        "stub_uk": stream_ticks_sim,
        "stub_de": stream_ticks_sim,
    }
    stream_fn = ADAPTERS.get(venue, stream_ticks_sim)

    STATE_PATH  = RUNTIME / f"state_{symbol}.json"
    PRICES_PATH = RUNTIME / f"prices_{symbol}.jsonl"

    async def telemetry():
        import json, time as _t
        while True:
            snap = {
                "ts": _t.time(),
                "symbol": symbol,
                "last_price": eng.last_price,
                "phase": eng.state.phase,
                "cycles": eng.state.cycles,
                "position": getattr(risk, "position", 0),
            }
            try:
                STATE_PATH.write_text(json.dumps(snap))
            except Exception:
                pass
            await asyncio.sleep(1)

    async def price_tap():
        import json, time as _t
        while True:
            if eng.last_price is not None:
                try:
                    with open(PRICES_PATH, "a") as f:
                        f.write(json.dumps({"ts": _t.time(), "price": eng.last_price}) + "\n")
                except Exception:
                    pass
            await asyncio.sleep(0.5)

    async def exec_consumer():
        import csv, time as _t
        csv_path = RUNTIME / f"trades_{symbol}.csv"
        header_written = csv_path.exists()
        try:
            from slack_notifier import notify
        except Exception:
            notify = lambda text: None
        try:
            from signal_explainer import explain
        except Exception:
            def explain(sym, reason, fb, ff, phase, cycles, last, pos):
                return f"{sym} {reason} | phase={phase} cycles={cycles} last={last} pos={pos}"

        while True:
            e: Execution = await exec_q.get()
            risk.on_fill(e.side, e.qty, e.price)
            print(f"[{symbol}] [EXEC] {e.side} {e.qty} @ {e.price}")
            try:
                with open(csv_path, "a", newline="") as cf:
                    w = csv.writer(cf)
                    if not header_written:
                        w.writerow(["ts","side","qty","price"]); header_written = True
                    w.writerow([_t.time(), e.side, e.qty, e.price])
                note = explain(symbol, getattr(e, "reason", "EXEC"), None, None,
                               eng.state.phase, eng.state.cycles, eng.last_price, risk.position)
                notify(f"[{symbol}] {note}")
            except Exception:
                pass

    tasks = [
        asyncio.create_task(stream_fn(symbol, ticks_q)),
        asyncio.create_task(eng.run()),
        asyncio.create_task(risk.run(signals_q, approvals_q)),
        asyncio.create_task(oms.run(approvals_q)),
        asyncio.create_task(exec_consumer()),
        asyncio.create_task(telemetry()),
        asyncio.create_task(price_tap()),
    ]
    await asyncio.gather(*tasks)

async def main():
    venues = CONFIG["venues"]
    coros = [launch_symbol(s, venues[s["venue"]]) for s in CONFIG["symbols"]]
    await asyncio.gather(*coros)

if __name__ == "__main__":
    asyncio.run(main())
PY
