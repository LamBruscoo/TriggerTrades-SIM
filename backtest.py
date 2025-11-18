import asyncio, csv, argparse, datetime as dt
from config import SETTINGS
from strategy_engine import StrategyEngine
from risk_gate import RiskGate
from oms_router import OMSRouter
from events import Tick, Execution, OrderApproved, OrderSignal
import time

async def feed_csv(path, ticks_q: asyncio.Queue, speed: float = 0.0):
    # CSV columns: ts,price,size   ts = ISO8601 or epoch ns
    with open(path, "r", newline="") as f:
        rdr = csv.DictReader(f)
        last_ts = None
        for row in rdr:
            ts_raw = row["ts"]
            price = float(row["price"])
            size = int(row.get("size", "0"))
            try:
                # try epoch ns
                ts_ns = int(ts_raw)
            except ValueError:
                # try ISO
                ts_ns = int(dt.datetime.fromisoformat(ts_raw).timestamp() * 1e9)
            if last_ts and speed > 0:
                # simulate pacing
                delta = (ts_ns - last_ts) / 1e9 / speed
                await asyncio.sleep(max(0.0, min(delta, 0.2)))
            last_ts = ts_ns
            await ticks_q.put(Tick(ts_ns=ts_ns, symbol=SETTINGS.symbol, price=price, size=size))

async def main(args):
    ticks_q = asyncio.Queue()
    signals_q = asyncio.Queue()
    approvals_q = asyncio.Queue()
    exec_q = asyncio.Queue()

    engine = StrategyEngine(ticks_q, signals_q)
    risk = RiskGate()

    class FakeOMS:
        async def run(self, approvals_q):
            while True:
                appr = await approvals_q.get()
                # immediate synthetic fill @ last known price (for demo)
                px = engine.last_price or 0.0
                await exec_q.put(Execution(ts_ns=appr.ts_ns, symbol=appr.symbol, side=appr.side, qty=appr.qty, price=px))

    async def exec_consumer():
        fills = 0
        while True:
            e: Execution = await exec_q.get()
            fills += 1
            risk.on_fill(e.side, e.qty, e.price)
            if fills % 50 == 0:
                print(f"[BT] Fills: {fills}")

    tasks = [
        asyncio.create_task(feed_csv(args.csv, ticks_q, speed=args.speed)),
        asyncio.create_task(engine.run()),
        asyncio.create_task(risk.run(signals_q, approvals_q)),
        asyncio.create_task(FakeOMS().run(approvals_q)),
        asyncio.create_task(exec_consumer()),
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--speed", type=float, default=0.0, help=">0 to pace; 0 for as-fast-as-possible")
    args = ap.parse_args()
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        pass
