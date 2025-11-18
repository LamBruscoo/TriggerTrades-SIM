import os, json, asyncio, argparse, sys, time
import websockets
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def log(*a): print("[PROBE]", *a, file=sys.stderr)

def make_subscribe(channel: str, symbol: str):
    ch = (channel or "trades").lower()
    sym = (symbol or "DIA").upper()
    if ch == "quotes": return {"action":"subscribe","quotes":[sym]}
    if ch == "bars":   return {"action":"subscribe","bars":[sym]}
    return {"action":"subscribe","trades":[sym]}

async def main(args):
    key = os.getenv("ALPACA_KEY")
    sec = os.getenv("ALPACA_SECRET")
    url = os.getenv("ALPACA_WS_URL", "wss://stream.data.alpaca.markets/v2/iex")
    if not key or not sec:
        log("Missing ALPACA_KEY/ALPACA_SECRET")
        return
    auth = {"action":"auth","key":key,"secret":sec}
    sub = make_subscribe(args.channel, args.symbol)
    sym = sub.get('quotes',[args.symbol])[0] if args.channel=='quotes' else sub.get('bars',[args.symbol])[0] if args.channel=='bars' else sub.get('trades',[args.symbol])[0]
    log(f"Connecting to {url}, channel={args.channel}, symbol={sym}")
    try:
        async with websockets.connect(url, ping_interval=20, ping_timeout=20, close_timeout=5) as ws:
            await ws.send(json.dumps(auth))
            auth_resp_raw = await ws.recv()
            print(auth_resp_raw)
            # check auth success before subscribing
            if '"error"' in auth_resp_raw and '401' in auth_resp_raw:
                log("Auth failed (401). Verify keys & plan.")
                return
            await ws.send(json.dumps(sub))
            sub_resp_raw = await ws.recv()
            print(sub_resp_raw)
            if '"error"' in sub_resp_raw and '406' in sub_resp_raw:
                log("Connection limit exceeded (406). Close other processes using the data stream and retry in ~60s.")
                return
            if '"error"' in sub_resp_raw:
                log("Subscription error; response above.")
                return
            # attempt to read a few data messages with timeout
            got_tick = False
            for i in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                except asyncio.TimeoutError:
                    continue
                if '"T":"t"' in msg or '"T":"q"' in msg or '"T":"b"' in msg:
                    got_tick = True
                print(msg)
            if not got_tick:
                log("No ticks received during probe window. Causes: market closed, symbol sparse, feed type limited. Try SYMBOL=AAPL, channel=quotes, or ALPACA_WS_URL wss://stream.data.alpaca.markets/v2/sip if available.")
    except Exception as e:
        log("Probe failed:", repr(e))
        return

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="DIA")
    ap.add_argument("--channel", default="trades", choices=["trades","quotes","bars"])
    args = ap.parse_args()
    asyncio.run(main(args))
