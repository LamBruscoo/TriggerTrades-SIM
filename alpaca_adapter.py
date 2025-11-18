
import asyncio, os, json, time, sys
import websockets
from events import Tick
from config import SETTINGS

def log(*a): print("[ALPACA-WS]", *a, file=sys.stderr)

def make_subscribe(channel: str, symbol: str):
    ch = (channel or "trades").lower()
    sym = (symbol or "DIA").upper()
    if ch == "quotes": return {"action":"subscribe","quotes":[sym]}
    if ch == "bars":   return {"action":"subscribe","bars":[sym]}
    return {"action":"subscribe","trades":[sym]}

async def stream_ticks(symbol: str, out_queue: asyncio.Queue):
    WS_URL = os.getenv("ALPACA_WS_URL", "wss://stream.data.alpaca.markets/v2/iex")
    channel = os.getenv("ALPACA_CHANNEL", "trades").lower()
    key = SETTINGS.alpaca_key; secret = SETTINGS.alpaca_secret
    log_ticks = os.getenv("LOG_TICKS", "0").lower() in ("1","true","yes","on")
    
    # Debug information
    log("Debug: Checking environment setup:")
    log(f"Debug: ALPACA_KEY present: {'Yes' if os.getenv('ALPACA_KEY') else 'No'}")
    log(f"Debug: ALPACA_SECRET present: {'Yes' if os.getenv('ALPACA_SECRET') else 'No'}")
    log(f"Debug: SETTINGS.alpaca_key length: {len(key) if key else 0}")
    log(f"Debug: SETTINGS.alpaca_secret length: {len(secret) if secret else 0}")
    
    if not key or not secret:
        log("Error: Missing ALPACA_KEY/SECRET")
        await asyncio.sleep(5)
        return

    auth_msg = {"action":"auth","key": key,"secret": secret}
    subs_msg = make_subscribe(channel, symbol)
    sub_symbol = subs_msg.get('quotes',[symbol])[0] if channel=='quotes' else subs_msg.get('bars',[symbol])[0] if channel=='bars' else subs_msg.get('trades',[symbol])[0]
    log(f"Connecting to {WS_URL} channel={channel} symbol={sub_symbol}")

    backoff = 2.0
    no_tick_warn_after = float(os.getenv("NO_TICK_WARN_SEC", "15"))
    first_sub_time = None
    tick_count = 0
    fallback_requested = False
    while True:
        try:
            async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20, close_timeout=5) as ws:
                await ws.send(json.dumps(auth_msg))
                auth_resp_raw = await ws.recv()
                log("AUTH:", auth_resp_raw)
                try:
                    auth_resp = json.loads(auth_resp_raw)
                except Exception:
                    auth_resp = []
                # Proceed only if authenticated
                await ws.send(json.dumps(subs_msg))
                sub_resp_raw = await ws.recv()
                log("SUB:", sub_resp_raw)
                try:
                    sub_resp = json.loads(sub_resp_raw)
                except Exception:
                    sub_resp = []
                # Detect connection limit error 406 and back off / exit
                if isinstance(sub_resp, list) and any((isinstance(e, dict) and e.get('T')=='error' and e.get('code')==406) for e in sub_resp):
                    log("Connection limit exceeded (406). Backing off 60s and exiting stream.")
                    await asyncio.sleep(60)
                    return
                # Reset backoff on success
                backoff = 2.0
                # mark subscription start and write live mode marker
                first_sub_time = time.time()
                try:
                    import pathlib
                    runtime = pathlib.Path("runtime"); runtime.mkdir(exist_ok=True)
                    (runtime / "mode.txt").write_text("live")
                except Exception:
                    pass

                async def no_tick_watchdog():
                    nonlocal fallback_requested
                    await asyncio.sleep(no_tick_warn_after)
                    if tick_count == 0:
                        log(f"WARNING: No ticks received for {sub_symbol} on channel '{channel}' after {no_tick_warn_after}s. Using simulator fallback.")
                        fallback_requested = True
                        try:
                            await ws.close()
                        except Exception:
                            pass

                wd_task = asyncio.create_task(no_tick_watchdog())

                async for msg in ws:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue
                    if not isinstance(data, list):
                        continue
                    for d in data:
                        T = d.get("T"); S = d.get("S")
                        if T == "subscription":
                            # mark subscription start
                            first_sub_time = first_sub_time or time.time()
                            continue
                        if channel == "trades" and T == "t" and S == sub_symbol:
                            price = float(d.get("p", 0) or 0)
                            size = int(d.get("s", 0) or 0)
                            if price:
                                if log_ticks:
                                    log(f"tick trade {S} p={price} s={size}")
                                await out_queue.put(Tick(ts_ns=time.time_ns(), symbol=sub_symbol, price=price, size=size))
                                tick_count += 1
                        elif channel == "quotes" and T == "q" and S == sub_symbol:
                            bp = float(d.get("bp",0) or 0); ap = float(d.get("ap",0) or 0)
                            if bp and ap:
                                mid = (bp+ap)/2.0
                                if log_ticks:
                                    log(f"tick quote {S} bp={bp} ap={ap} mid={mid}")
                                await out_queue.put(Tick(ts_ns=time.time_ns(), symbol=sub_symbol, price=mid, size=0))
                                tick_count += 1
                        elif channel == "bars" and T == "b" and S == sub_symbol:
                            c = float(d.get("c",0) or 0)
                            if c:
                                if log_ticks:
                                    log(f"tick bar {S} c={c}")
                                await out_queue.put(Tick(ts_ns=time.time_ns(), symbol=sub_symbol, price=c, size=0))
                                tick_count += 1
                    if tick_count > 0 and not wd_task.done():
                        wd_task.cancel()
                # after websocket exits, check if watchdog requested fallback
                if fallback_requested and os.getenv("SIM_FALLBACK", "1").lower() in ("1","true","yes","on"):
                    try:
                        import pathlib
                        runtime = pathlib.Path("runtime"); runtime.mkdir(exist_ok=True)
                        (runtime / "mode.txt").write_text("sim")
                    except Exception:
                        pass
                    from sim_feed import stream_ticks as sim_stream
                    await sim_stream(symbol, out_queue)
                    return
        except Exception as e:
            log("Reconnect in", f"{backoff:.0f}s:", repr(e))
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
            continue
