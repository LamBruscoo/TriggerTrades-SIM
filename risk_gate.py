import asyncio, time
from events import OrderSignal, OrderApproved
from config import SETTINGS

class RiskGate:
    def __init__(self):
        self.position = 0
        self.daily_pnl = 0.0
        self._realized_pnl = 0.0
        self._avg_price = 0.0  # average entry price of current open position
        self._last_price = None
        self.last_order_ts = 0.0

    async def run(self, signals_q: asyncio.Queue, approvals_q: asyncio.Queue):
        while True:
            sig: OrderSignal = await signals_q.get()
            now = time.time()
            # throttle
            if now - self.last_order_ts < 1.0 / SETTINGS.order_throttle_per_sec:
                continue
            # position check
            new_pos = self.position + (sig.qty if sig.side == "BUY" else -sig.qty)
            if abs(new_pos) > SETTINGS.max_position:
                continue
            # daily loss check (in demo we don't mark-to-market; OMS updates pnl on fills)
            if self.daily_pnl <= -SETTINGS.daily_max_loss:
                continue
            self.last_order_ts = now
            await approvals_q.put(OrderApproved(
                ts_ns=sig.ts_ns, symbol=sig.symbol, side=sig.side, qty=sig.qty, reason=sig.reason
            ))

    def on_fill(self, side: str, qty: int, price: float):
        """Update position, avg price, and realized PnL on execution."""
        if price is None:
            price = 0.0
        delta = qty if side == "BUY" else -qty
        new_pos = self.position + delta

        # If adding to same-direction position, adjust average price
        if self.position == 0 or (self.position > 0 and delta > 0) or (self.position < 0 and delta < 0):
            # increasing exposure in same direction
            abs_pos = abs(self.position)
            if abs_pos + abs(delta) > 0:
                # compute new weighted average price
                self._avg_price = (
                    (self._avg_price * abs_pos + price * abs(delta)) / (abs_pos + abs(delta))
                ) if abs_pos > 0 else price
        else:
            # Reducing or flipping position: realize PnL on the closed shares
            close_qty = min(abs(qty), abs(self.position))
            if self.position > 0:
                # closing part of a long
                self._realized_pnl += (price - self._avg_price) * close_qty
            elif self.position < 0:
                # closing part of a short
                self._realized_pnl += (self._avg_price - price) * close_qty
            # If we fully crossed through zero, set avg_price to fill price for the remainder
            if abs(delta) > abs(self.position):
                # flipped to the other side; reset avg to entry of new side
                remainder = abs(delta) - abs(self.position)
                if remainder > 0:
                    self._avg_price = price

        self.position = new_pos

    def update_mark_to_market(self, last_price: float | None):
        """Recompute daily PnL as realized + unrealized based on last price."""
        self._last_price = last_price if isinstance(last_price, (int, float)) else None
        unreal = 0.0
        if self._last_price is not None and self.position != 0:
            if self.position > 0:
                unreal = (self._last_price - self._avg_price) * self.position
            else:
                unreal = (self._avg_price - self._last_price) * abs(self.position)
        self.daily_pnl = self._realized_pnl + unreal

    def reset_daily_pnl(self):
        """Reset daily PnL tracking for a fresh trading day."""
        self._realized_pnl = 0.0
        self.daily_pnl = 0.0
        print("[RISK] Daily PnL reset to 0.0")
