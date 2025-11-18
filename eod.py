import asyncio, datetime as dt
from zoneinfo import ZoneInfo
from config import SETTINGS

def next_close(now: dt.datetime) -> dt.datetime:
    # Compute today's or next market close at EOD_HHMM in TZ
    hh, mm = map(int, SETTINGS.eod_hhmm.split(":"))
    today_close = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if now >= today_close:
        # next weekday
        nxt = now + dt.timedelta(days=1)
        while nxt.weekday() >= 5:  # skip Sat/Sun
            nxt += dt.timedelta(days=1)
        return nxt.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return today_close

async def eod_watcher(flatten_cb, reset_cb):
    while True:
        now = dt.datetime.now(SETTINGS.zone)
        target = next_close(now)
        await asyncio.sleep((target - now).total_seconds())
        try:
            await flatten_cb()
        finally:
            reset_cb()
