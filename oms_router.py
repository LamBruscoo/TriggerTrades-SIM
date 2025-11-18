import asyncio, time, httpx, json
from events import OrderApproved, Execution
from config import SETTINGS

class OMSRouter:
    def __init__(self, exec_q: asyncio.Queue, engine=None, mode="live"):
        self.exec_q = exec_q
        self.engine = engine  # Reference to get current price in sim mode
        self.mode = mode  # "live" or "sim"
        self.base = SETTINGS.alpaca_base.rstrip('/')
        self.key = SETTINGS.alpaca_key
        self.secret = SETTINGS.alpaca_secret
        self.headers = {
            "APCA-API-KEY-ID": self.key,
            "APCA-API-SECRET-KEY": self.secret,
            "Content-Type": "application/json"
        }

    async def place_order(self, symbol: str, side: str, qty: int, typ="market", tif="day"):
        url = f"{self.base}/v2/orders"
        data = {"symbol": symbol, "side": side.lower(), "type": typ, "time_in_force": tif, "qty": qty}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, headers=self.headers, json=data)
            r.raise_for_status()
            j = r.json()
            try:
                print("[OMS] Order response:", j)
            except Exception:
                pass
            # For the demo, assume immediate fill. In reality, poll order status or subscribe to trade updates.
            px = None
            try:
                px = float(j.get("filled_avg_price") or 0) or None
            except Exception:
                px = None
            return px

    async def run(self, approvals_q: asyncio.Queue):
        while True:
            appr: OrderApproved = await approvals_q.get()
            px = None
            
            # In sim mode, use current price from engine instead of placing real orders
            if self.mode == "sim" and self.engine and self.engine.last_price is not None:
                px = self.engine.last_price
                print(f"[OMS-SIM] {appr.side} {appr.qty} @ {px:.2f} (reason: {appr.reason})")
            else:
                # Live mode: place actual order
                try:
                    px = await self.place_order(SETTINGS.symbol, appr.side, appr.qty)
                except Exception as e:
                    print(f"[OMS-ERROR] Order failed: {e}")
                    # In case of error, use engine price as fallback
                    if self.engine and self.engine.last_price is not None:
                        px = self.engine.last_price
            
            exec_evt = Execution(ts_ns=appr.ts_ns, symbol=appr.symbol, side=appr.side, qty=appr.qty, price=px or 0.0, reason=appr.reason)
            await self.exec_q.put(exec_evt)
