from dataclasses import dataclass, field
from typing import Optional, Literal
import time

@dataclass
class Tick:
    ts_ns: int
    symbol: str
    price: float
    size: int = 0

@dataclass
class OrderSignal:
    ts_ns: int
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: int
    reason: str
    base_price: float
    first_order_price: float | None
    from_base_pts: float
    from_first_pts: float | None

@dataclass
class OrderApproved:
    ts_ns: int
    symbol: str
    side: str
    qty: int
    reason: str

@dataclass
class Execution:
    ts_ns: int
    symbol: str
    side: str
    qty: int
    price: float
    status: str = "filled"
    reason: str = ""
