# strategy_engine.py
import asyncio, time
from dataclasses import dataclass
from typing import Optional

from events import Tick, OrderSignal
from config import SETTINGS


@dataclass
class LadderState:
    base_price: Optional[float] = None
    first_order_price: Optional[float] = None
    t3_anchor: Optional[float] = None
    t4_anchor: Optional[float] = None
    phase: str = "IDLE"
    cycles: int = 0
    last_beat_price: Optional[float] = None
    last_jump_dir: Optional[int] = None
    # Extended state for T10-T16 triggers
    t9_last_position_price: Optional[float] = None
    t9_last_position_side: Optional[str] = None
    t11_start_price: Optional[float] = None
    t11_start_cycle: int = 0
    last_position_price: Optional[float] = None  # For counter triggers T12/T13
    last_position_side: Optional[str] = None
    t12_triggered: bool = False
    t15_window_start: Optional[float] = None  # for T15 low volatility
    t15_window_start_cycle: int = 0
    t16_fallback_cycle: int = 0  # for T16


class StrategyEngine:
    def __init__(self, ticks_q: asyncio.Queue, signals_q: asyncio.Queue, symbol: Optional[str] = None, risk_gate=None):
        self.ticks_q = ticks_q
        self.signals_q = signals_q
        self.risk_gate = risk_gate  # For protection cycle position tracking
        self.state = LadderState()
        self.last_price: Optional[float] = None
        self._stop = False
        self.tick_count = 0
        self._last_tick_ts: float | None = None
        # symbol for emitted signals (defaults to global SETTINGS)
        self.symbol = (symbol or SETTINGS.symbol)
        # beat can be overridden per-session (used by run_multi)
        self.beat_sec: float = SETTINGS.beat_sec
        # per-instance lots (overridable for multi-symbol runs)
        self.lots = {
            "T1": SETTINGS.lot_t1,
            "T2": SETTINGS.lot_t2,
            "T3": SETTINGS.lot_t3,
            "T4": SETTINGS.lot_t4,
            "T5": SETTINGS.lot_t5,
            "T7": SETTINGS.lot_t7,
            "T8": SETTINGS.lot_t8,
            "T9": SETTINGS.lot_t9,
            "T10": SETTINGS.lot_t10,
            "T11": SETTINGS.lot_t11,
            "T12": SETTINGS.lot_t12,
            "T13": SETTINGS.lot_t13,
            "T14": SETTINGS.lot_t14,
            "T15": SETTINGS.lot_t15,
            "T16": SETTINGS.lot_t16,
        }
        
        # Price history for slow trend detection (T11)
        self.price_history: list[tuple[float, float]] = []  # (timestamp, price)

    def set_lots(self, *args, **kwargs):
        """Overridable lot config for multi-symbol."""
        pass

    def set_atr_params(self, *args, **kwargs):
        """Placeholder for compatibility."""
        pass

    def set_beat(self, beat_sec: float):
        """Override beat interval."""
        self.beat_sec = beat_sec

    async def tick_listener(self):
        """Consume ticks and update last_price."""
        while not self._stop:
            t: Tick = await self.ticks_q.get()
            self.last_price = t.price
            self.tick_count += 1
            self._last_tick_ts = time.time()

    async def beat_loop(self):
        """14-second beat cycle evaluating all 16 entry triggers (T1-T16)."""
        while not self._stop:
            await asyncio.sleep(self.beat_sec)
            if self.last_price is None:
                continue
            
            # Check if trading is paused
            import pathlib
            if pathlib.Path("runtime/pause.flag").exists():
                # Skip signal generation when paused
                continue
            
            price = self.last_price
            s = self.state
            
            # Track price history for T11 (slow trend)
            now = time.time()
            self.price_history.append((now, price))
            # Keep only last 15 minutes of history
            cutoff = now - (15 * 60)
            self.price_history = [(t, p) for t, p in self.price_history if t >= cutoff]
            
            # === T14: Violent Swing (always active, any direction) ===
            if s.base_price is not None and abs(price - s.base_price) >= SETTINGS.t14_violent_swing:
                side = "BUY" if price > s.base_price else "SELL"
                await self.emit_signal(price, "T14", self.lots["T14"], s, price - s.base_price, None)
            
            # === IDLE state initialization ===
            if s.phase == "IDLE":
                s.base_price = price
                s.first_order_price = None
                s.t3_anchor = None
                s.t4_anchor = None
                s.cycles = 0
                s.phase = "T1_WINDOW"
                s.last_beat_price = price
                s.last_jump_dir = None
                s.t11_start_price = price
                s.t11_start_cycle = 0
                s.t15_window_start = price
                s.t15_window_start_cycle = 0
                s.t16_fallback_cycle = 0
                continue
            
            s.cycles += 1
            from_base = price - (s.base_price or price)
            
            # === T8/T9: Jump Detection (directional entry) ===
            if s.last_beat_price is not None:
                jump = abs(price - s.last_beat_price)
                direction = 1 if (price - s.last_beat_price) > 0 else (-1 if (price - s.last_beat_price) < 0 else 0)
                
                if s.last_jump_dir is None and jump >= SETTINGS.t8_jump_single and direction != 0:
                    # T8: First jump detected
                    await self.emit_signal(price, "T8", self.lots["T8"], s, from_base, None)
                    s.last_jump_dir = direction
                    s.t9_last_position_price = price
                    s.t9_last_position_side = "BUY" if direction > 0 else "SELL"
                    
                elif s.last_jump_dir == direction and jump >= SETTINGS.t9_jump2_single and direction != 0:
                    # T9: Second jump in same direction
                    await self.emit_signal(price, "T9", self.lots["T9"], s, from_base, None)
                    s.last_jump_dir = None  # Reset after T9
                    s.t9_last_position_price = price
                    s.t9_last_position_side = "BUY" if direction > 0 else "SELL"
            
            # === T10: Post-5K Extension (favorable move after T7/T9) ===
            if s.t9_last_position_price is not None and s.t9_last_position_side is not None:
                if s.t9_last_position_side == "BUY":
                    favorable = price - s.t9_last_position_price
                    if favorable >= SETTINGS.t10_favorable_move:
                        await self.emit_signal(price, "T10", self.lots["T10"], s, from_base, None)
                        s.t9_last_position_price = None  # Reset
                elif s.t9_last_position_side == "SELL":
                    favorable = s.t9_last_position_price - price
                    if favorable >= SETTINGS.t10_favorable_move:
                        await self.emit_signal(price, "T10", self.lots["T10"], s, from_base, None)
                        s.t9_last_position_price = None  # Reset
            
            # === T11: Slow Trend (65-beat window, ~15 minutes) ===
            if len(self.price_history) >= SETTINGS.t11_window_beats:
                window_start_price = self.price_history[0][1]
                move = abs(price - window_start_price)
                if move >= SETTINGS.t11_slow_trend:
                    side = "BUY" if price > window_start_price else "SELL"
                    await self.emit_signal(price, "T11", self.lots["T11"], s, from_base, None)
                    # Reset window
                    self.price_history = [(now, price)]
            
            # === T12/T13: Counter-Position Sequence (opposite direction) ===
            if s.last_position_side is not None and s.last_position_price is not None:
                if not s.t12_triggered:
                    # Check for T12: counter jump
                    if s.last_position_side == "BUY":
                        counter_move = s.last_position_price - price  # Price dropped
                        if counter_move >= SETTINGS.t12_counter_jump:
                            await self.emit_signal(price, "T12", self.lots["T12"], s, from_base, None)
                            s.t12_triggered = True
                    elif s.last_position_side == "SELL":
                        counter_move = price - s.last_position_price  # Price rose
                        if counter_move >= SETTINGS.t12_counter_jump:
                            await self.emit_signal(price, "T12", self.lots["T12"], s, from_base, None)
                            s.t12_triggered = True
                else:
                    # T13: continuation of counter move
                    if s.last_position_side == "BUY":
                        additional = s.last_position_price - price
                        if additional >= (SETTINGS.t12_counter_jump + SETTINGS.t13_counter_continue):
                            await self.emit_signal(price, "T13", self.lots["T13"], s, from_base, None)
                            s.t12_triggered = False  # Reset
                    elif s.last_position_side == "SELL":
                        additional = price - s.last_position_price
                        if additional >= (SETTINGS.t12_counter_jump + SETTINGS.t13_counter_continue):
                            await self.emit_signal(price, "T13", self.lots["T13"], s, from_base, None)
                            s.t12_triggered = False  # Reset
            
            # === T15: Low Volatility Strategy (34-beat/9-min window) ===
            if s.t15_window_start_cycle == 0:
                s.t15_window_start = price
                s.t15_window_start_cycle = s.cycles
            elif (s.cycles - s.t15_window_start_cycle) >= SETTINGS.t15_low_vol_window:
                # Check if range is below threshold
                window_range = abs(price - s.t15_window_start)
                if window_range <= SETTINGS.t15_low_vol_threshold:
                    # Low volatility detected, check for move
                    if window_range >= SETTINGS.t15_move_mark:
                        side = "BUY" if price > s.t15_window_start else "SELL"
                        await self.emit_signal(price, "T15", self.lots["T15"], s, from_base, None)
                # Reset window
                s.t15_window_start = price
                s.t15_window_start_cycle = s.cycles
            
            # === T16: Fallback Directional (after 11 beats without T1-T5) ===
            if s.phase == "T1_WINDOW" and s.cycles >= SETTINGS.t16_fallback_window:
                if abs(from_base) >= SETTINGS.t16_fallback_move:
                    side = "BUY" if from_base > 0 else "SELL"
                    await self.emit_signal(price, "T16", self.lots["T16"], s, from_base, None)
                    s.phase = "IDLE"  # Reset after T16
            
            # === T1-T5 Ladder Logic ===
            if s.phase == "T1_WINDOW":
                if s.cycles <= 4 and abs(from_base) >= SETTINGS.t1_move:
                    await self.emit_signal(price, "T1", self.lots["T1"], s, from_base, None)
                    s.first_order_price = price
                    s.last_position_price = price
                    s.last_position_side = "BUY" if from_base > 0 else "SELL"
                    s.phase = "T2_WINDOW"
                    s.cycles = 0
                    s.t3_anchor = price
                elif s.cycles > 4:
                    s.phase = "IDLE"
            
            elif s.phase == "T2_WINDOW":
                if s.cycles <= 4 and abs(from_base) >= SETTINGS.t2_hold:
                    from_first = (price - s.first_order_price) if s.first_order_price else None
                    await self.emit_signal(price, "T2", self.lots["T2"], s, from_base, from_first)
                    s.last_position_price = price
                    s.last_position_side = "BUY" if from_base > 0 else "SELL"
                    s.phase = "T3_WINDOW"
                    s.cycles = 0
                    s.t3_anchor = price
                elif s.cycles > 4:
                    s.phase = "IDLE"
            
            elif s.phase == "T3_WINDOW":
                from_first = (price - s.first_order_price) if s.first_order_price else 0.0
                if s.cycles <= 3 and abs(from_first) >= SETTINGS.t3_move_from_t0:
                    await self.emit_signal(price, "T3", self.lots["T3"], s, from_base, from_first)
                    s.last_position_price = price
                    s.last_position_side = "BUY" if from_first > 0 else "SELL"
                    s.phase = "T4_WINDOW"
                    s.cycles = 0
                    s.t4_anchor = price
                elif s.cycles > 3:
                    s.phase = "IDLE"
            
            elif s.phase == "T4_WINDOW":
                delta = abs(price - (s.t3_anchor or price))
                if s.cycles <= 2 and delta >= SETTINGS.t4_extra_from_t3:
                    from_first = (price - s.first_order_price) if s.first_order_price else None
                    await self.emit_signal(price, "T4", self.lots["T4"], s, from_base, from_first)
                    s.last_position_price = price
                    s.last_position_side = "BUY" if from_base > 0 else "SELL"
                    s.phase = "T5_WINDOW"
                    s.cycles = 0
                elif s.cycles > 2:
                    s.phase = "IDLE"
            
            elif s.phase == "T5_WINDOW":
                delta = abs(price - (s.t4_anchor or price))
                if s.cycles <= 3 and delta >= SETTINGS.t5_extra_from_t4:
                    from_first = (price - s.first_order_price) if s.first_order_price else None
                    await self.emit_signal(price, "T5", self.lots["T5"], s, from_base, from_first)
                    s.last_position_price = price
                    s.last_position_side = "BUY" if from_base > 0 else "SELL"
                    s.phase = "IDLE"
                elif s.cycles > 3:
                    s.phase = "IDLE"
            
            # === T7: Macro Move from First Order ===
            if s.first_order_price is not None:
                total_from_first = abs(price - s.first_order_price)
                if total_from_first >= SETTINGS.t7_total_from_first:
                    from_first = price - s.first_order_price
                    await self.emit_signal(price, "T7", self.lots["T7"], s, from_base, from_first)
                    s.last_position_price = price
                    s.last_position_side = "BUY" if from_first > 0 else "SELL"
                    s.t9_last_position_price = price  # Enable T10 after T7
                    s.t9_last_position_side = "BUY" if from_first > 0 else "SELL"
            
            s.last_beat_price = price

    async def emit_signal(self, price: float, reason: str, qty: int,
                          s: LadderState, from_base_pts: float,
                          from_first_pts: Optional[float]):
        """Emit trading signal with proper formatting."""
        direction = from_first_pts if from_first_pts is not None else from_base_pts
        side = "BUY" if direction > 0 else "SELL"
        
        sig = OrderSignal(
            ts_ns=time.time_ns(),
            symbol=self.symbol,
            side=side,
            qty=qty,
            reason=reason,
            base_price=s.base_price or price,
            first_order_price=s.first_order_price,
            from_base_pts=from_base_pts,
            from_first_pts=from_first_pts
        )
        
        # Format for logging (handle None values)
        try:
            fb_str = f"+{from_base_pts:.2f}" if from_base_pts >= 0 else f"{from_base_pts:.2f}"
            ff_str = f"+{from_first_pts:.2f}" if from_first_pts and from_first_pts >= 0 else (f"{from_first_pts:.2f}" if from_first_pts else "—")
            print(f"[SIGNAL] {reason} {sig.side} {sig.qty} base={sig.base_price:.2f} last={price:.2f} from_base={fb_str} from_first={ff_str}")
        except Exception:
            print(f"[SIGNAL] {reason} {sig.side} {sig.qty} last={price} from_base={from_base_pts} from_first={from_first_pts}")
        
        await self.signals_q.put(sig)

    async def protection_cycle(self):
        """37-second protection cycle: monitors positions and exits on adverse moves"""
        while not self._stop:
            await asyncio.sleep(SETTINGS.alt_beat_sec)  # 37 seconds
            
            if self.last_price is None or self.risk_gate is None:
                continue
            
            p = self.last_price
            rg = self.risk_gate
            
            # Protection logic: Exit if stop loss hit OR take profit target reached
            if rg.position == 0:
                continue
            
            # Calculate adverse move (loss) and favorable move (profit) from average entry price
            adverse_move = 0.0
            favorable_move = 0.0
            
            if rg.position > 0:
                # We're long
                adverse_move = rg._avg_price - p  # loss = entry - current
                favorable_move = p - rg._avg_price  # profit = current - entry
            else:
                # We're short
                adverse_move = p - rg._avg_price  # loss = current - entry
                favorable_move = rg._avg_price - p  # profit = entry - current
            
            # Exit on stop loss (1.50 pts adverse) OR take profit (2.00 pts favorable)
            should_exit = False
            exit_reason = ""
            
            if adverse_move >= SETTINGS.per_leg_stop_pts:
                should_exit = True
                exit_reason = f"STOP LOSS (adverse: {adverse_move:.2f} pts)"
            elif favorable_move >= 2.00:  # Take profit at 2.00 points gain
                should_exit = True
                exit_reason = f"TAKE PROFIT (gain: {favorable_move:.2f} pts)"
            
            if should_exit:
                exit_side = "SELL" if rg.position > 0 else "BUY"
                exit_qty = abs(rg.position)
                
                sig = OrderSignal(
                    ts_ns=time.time_ns(),
                    symbol=self.symbol,
                    side=exit_side,
                    qty=exit_qty,
                    reason="PROTECT",
                    base_price=self.state.base_price or p,
                    first_order_price=self.state.first_order_price,
                    from_base_pts=None,
                    from_first_pts=None
                )
                print(f"[PROTECTION] {exit_reason} - {exit_side} {exit_qty} @ {p:.2f} (avg entry: {rg._avg_price:.2f})")
                await self.signals_q.put(sig)

    def reset_state(self):
        self.state = LadderState()
        self.price_history = []

    async def run(self):
        await asyncio.gather(
            self.tick_listener(), 
            self.beat_loop(),
            self.protection_cycle()
        )
