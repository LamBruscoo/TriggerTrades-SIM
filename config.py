import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

@dataclass
class Settings:
    symbol: str = os.getenv("SYMBOL", "DIA")
    tz: str = os.getenv("TZ", "America/New_York")
    # Alpaca
    # Read Alpaca API credentials from environment variables.
    # Use ALPACA_KEY and ALPACA_SECRET (defaults to empty string when not set).
    alpaca_key: str = os.getenv("AKWH3NKO7CRBARYWIHW7HXYV3X", "")
    alpaca_secret: str = os.getenv("3LsSTjQmE4igKxCJzANbU2ksy4nqEf8YFkZMYaJygFaS ", "")
    alpaca_base: str = os.getenv("ALPACA_PAPER_BASE", "https://paper-api.alpaca.markets/v2")
    # Beats (seconds)
    beat_sec: float = float(os.getenv("BEAT_SEC", "14"))
    alt_beat_sec: float = float(os.getenv("ALT_BEAT_SEC", "37"))
    # Triggers (points)
    t1_move: float = float(os.getenv("T1_MOVE", "0.14"))
    t2_hold: float = float(os.getenv("T2_HOLD", "0.18"))
    t3_move_from_t0: float = float(os.getenv("T3_MOVE_FROM_T0", "0.25"))
    t4_extra_from_t3: float = float(os.getenv("T4_EXTRA_FROM_T3", "0.10"))
    t5_extra_from_t4: float = float(os.getenv("T5_EXTRA_FROM_T4", "0.10"))
    t7_total_from_first: float = float(os.getenv("T7_TOTAL_FROM_FIRST", "0.80"))
    t8_jump_single: float = float(os.getenv("T8_JUMP_SINGLE", "0.16"))
    t9_jump2_single: float = float(os.getenv("T9_JUMP2_SINGLE", "0.14"))
    t10_favorable_move: float = float(os.getenv("T10_FAVORABLE_MOVE", "0.19"))  # 0.0004 * 475 ≈ 0.19
    t11_slow_trend: float = float(os.getenv("T11_SLOW_TREND", "0.52"))  # 0.0011 * 475 ≈ 0.52
    t11_window_beats: int = int(os.getenv("T11_WINDOW_BEATS", "65"))  # 15 minutes
    t12_counter_jump: float = float(os.getenv("T12_COUNTER_JUMP", "0.29"))  # 0.0006 * 475 ≈ 0.29
    t13_counter_continue: float = float(os.getenv("T13_COUNTER_CONTINUE", "0.09"))  # 0.00018 * 475 ≈ 0.09
    t14_violent_swing: float = float(os.getenv("T14_VIOLENT_SWING", "0.48"))  # 0.001 * 475 ≈ 0.48
    t15_low_vol_window: int = int(os.getenv("T15_LOW_VOL_WINDOW", "34"))  # 9 minutes
    t15_low_vol_threshold: float = float(os.getenv("T15_LOW_VOL_THRESHOLD", "0.29"))  # 0.0006 * 475
    t15_move_mark: float = float(os.getenv("T15_MOVE_MARK", "0.11"))  # 0.00024 * 475
    t16_fallback_window: int = int(os.getenv("T16_FALLBACK_WINDOW", "11"))
    t16_fallback_move: float = float(os.getenv("T16_FALLBACK_MOVE", "0.10"))  # 0.0002 * 475
    # Lots
    lot_t1: int = int(os.getenv("LOT_T1", "10"))
    lot_t2: int = int(os.getenv("LOT_T2", "10"))
    lot_t3: int = int(os.getenv("LOT_T3", "30"))
    lot_t4: int = int(os.getenv("LOT_T4", "200"))
    lot_t5: int = int(os.getenv("LOT_T5", "500"))
    lot_t7: int = int(os.getenv("LOT_T7", "5000"))
    lot_t8: int = int(os.getenv("LOT_T8", "1000"))
    lot_t9: int = int(os.getenv("LOT_T9", "5000"))
    lot_t10: int = int(os.getenv("LOT_T10", "1000"))
    lot_t11: int = int(os.getenv("LOT_T11", "1000"))
    lot_t12: int = int(os.getenv("LOT_T12", "400"))
    lot_t13: int = int(os.getenv("LOT_T13", "200"))
    lot_t14: int = int(os.getenv("LOT_T14", "1000"))
    lot_t15: int = int(os.getenv("LOT_T15", "100"))
    lot_t16: int = int(os.getenv("LOT_T16", "100"))
    # Risk
    max_position: int = int(os.getenv("MAX_POSITION", "10000"))
    daily_max_loss: float = float(os.getenv("DAILY_MAX_LOSS", "2000"))
    per_leg_stop_pts: float = float(os.getenv("PER_LEG_STOP_PTS", "1.50"))  # Wider stop = more room for profits
    order_throttle_per_sec: float = float(os.getenv("ORDER_THROTTLE_PER_SEC", "2"))
    # EOD
    eod_hhmm: str = os.getenv("EOD_HHMM", "16:00")
    # Zero Out & Reset
    enable_manual_reset: bool = os.getenv("ENABLE_MANUAL_RESET", "true").lower() in ("1","true","yes","on")
    # Feature Flags
    enable_gpt5_for_all_clients: bool = os.getenv("ENABLE_GPT5_FOR_ALL_CLIENTS", "false").lower() in ("1","true","yes","on")

    @property
    def zone(self):
        return ZoneInfo(self.tz)

SETTINGS = Settings()
