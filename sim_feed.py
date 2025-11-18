# sim_feed.py — synthetic tick generator (wiggles DIA price so triggers fire)
import asyncio, time, math, random, os
from events import Tick

async def stream_ticks(symbol: str, out_queue: asyncio.Queue):
    base = float(os.getenv("SIM_BASE_PRICE", "476.50"))
    amp = float(os.getenv("SIM_AMP", "0.30"))  # Reduced volatility for smoother trends
    noise = float(os.getenv("SIM_NOISE", "0.02"))  # Less noise for cleaner moves
    trend_strength = float(os.getenv("SIM_TREND", "0.02"))  # Upward drift per tick
    print(f"[SIM] starting feed for {symbol} base={base} amp={amp} noise={noise} trend={trend_strength}")
    t = 0
    drift = 0.0
    while True:
        # Smooth sine wave + gradual trend + small noise
        drift += trend_strength
        price = base + drift + amp*math.sin(t/8.0) + random.uniform(-noise, noise)
        await out_queue.put(Tick(ts_ns=time.time_ns(), symbol=symbol, price=round(price, 2), size=0))
        t += 1
        # Reverse trend every ~2 minutes to create realistic market cycles
        if t % 240 == 0:  # Every 240 ticks = 2 minutes
            trend_strength = -trend_strength
        await asyncio.sleep(0.5)  # 2 ticks/sec
