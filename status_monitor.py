#!/usr/bin/env python3
"""
Trading Status Monitor - Real-time display of strategy state
"""
import json
import time
import pathlib
from datetime import datetime
from typing import Optional

def clear_screen():
    """Clear terminal screen"""
    print("\033[2J\033[H", end="")

def get_state() -> Optional[dict]:
    """Read current state"""
    try:
        return json.loads(pathlib.Path("runtime/state.json").read_text())
    except:
        return None

def get_position() -> int:
    """Calculate position from trades"""
    position = 0
    try:
        with pathlib.Path("runtime/trades.jsonl").open("r") as f:
            for line in f:
                trade = json.loads(line.strip())
                qty = trade.get("qty", 0)
                side = trade.get("side", "")
                if side == "BUY":
                    position += qty
                elif side == "SELL":
                    position -= qty
    except:
        pass
    return position

def get_pnl() -> float:
    """Calculate approximate PnL from trades"""
    trades = []
    try:
        with pathlib.Path("runtime/trades.jsonl").open("r") as f:
            for line in f:
                trades.append(json.loads(line.strip()))
    except:
        return 0.0
    
    if not trades:
        return 0.0
    
    # Simple PnL calculation
    position = 0
    avg_entry = 0.0
    realized = 0.0
    
    for trade in trades:
        qty = trade.get("qty", 0)
        price = trade.get("price", 0.0)
        side = trade.get("side", "")
        
        if side == "BUY":
            if position >= 0:
                # Adding to long or entering long
                avg_entry = ((avg_entry * abs(position)) + (price * qty)) / (abs(position) + qty) if position > 0 else price
                position += qty
            else:
                # Covering short
                close_qty = min(qty, abs(position))
                realized += (avg_entry - price) * close_qty
                position += qty
        elif side == "SELL":
            if position <= 0:
                # Adding to short or entering short
                avg_entry = ((avg_entry * abs(position)) + (price * qty)) / (abs(position) + qty) if position < 0 else price
                position -= qty
            else:
                # Closing long
                close_qty = min(qty, abs(position))
                realized += (price - avg_entry) * close_qty
                position -= qty
    
    return realized

def format_time(ts: float) -> str:
    """Format timestamp"""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")

def main():
    """Display live status"""
    print("Starting status monitor... (Ctrl+C to exit)")
    time.sleep(1)
    
    try:
        while True:
            clear_screen()
            state = get_state()
            position = get_position()
            pnl = get_pnl()
            
            print("╔═══════════════════════════════════════════════════════════════╗")
            print("║            TRIGGERTRADES LIVE STATUS MONITOR                  ║")
            print("╚═══════════════════════════════════════════════════════════════╝")
            print()
            
            if state:
                # Strategy State
                phase = state.get("phase", "UNKNOWN")
                phase_color = "\033[92m" if phase == "IDLE" or phase.startswith("T") else "\033[93m"
                print(f"Strategy Phase:  {phase_color}{phase}\033[0m")
                print(f"Cycles:          {state.get('cycles', 0)}")
                print(f"Mode:            {state.get('mode', 'unknown').upper()}")
                
                # Prices
                print()
                last_price = state.get('last_price')
                base_price = state.get('base_price')
                first_price = state.get('first_order_price')
                
                if last_price:
                    print(f"Last Price:      ${last_price:.2f}")
                if base_price:
                    print(f"Base Price:      ${base_price:.2f}")
                    if last_price:
                        diff = last_price - base_price
                        color = "\033[92m" if diff > 0 else "\033[91m" if diff < 0 else "\033[0m"
                        print(f"From Base:       {color}{diff:+.2f}\033[0m")
                
                if first_price:
                    print(f"First Order:     ${first_price:.2f}")
                    if last_price:
                        diff = last_price - first_price
                        color = "\033[92m" if diff > 0 else "\033[91m" if diff < 0 else "\033[0m"
                        print(f"From First:      {color}{diff:+.2f}\033[0m")
                
                # Tick age
                tick_age = state.get('last_tick_age')
                if tick_age is not None:
                    tick_status = "✓ LIVE" if tick_age < 5 else "⚠ STALE"
                    print(f"\nTick Age:        {tick_age:.1f}s {tick_status}")
                
                # Timestamp
                ts = state.get('ts')
                if ts:
                    print(f"Updated:         {format_time(ts)}")
            else:
                print("⚠ State file not found or unreadable")
            
            # Position & PnL
            print()
            print("─" * 63)
            pos_color = "\033[92m" if position > 0 else "\033[91m" if position < 0 else "\033[0m"
            print(f"Position:        {pos_color}{position:+d}\033[0m shares")
            
            pnl_color = "\033[92m" if pnl > 0 else "\033[91m" if pnl < 0 else "\033[0m"
            print(f"Realized P&L:    {pnl_color}${pnl:+.2f}\033[0m")
            print("─" * 63)
            
            # Controls
            print()
            print("Commands:")
            print("  ./reset_trading.sh      → Zero out & reset")
            print("  python reset_trading.py --status  → Detailed status")
            print("  Ctrl+C                  → Exit monitor")
            
            print()
            print(f"Refreshing...  [{datetime.now().strftime('%H:%M:%S')}]")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStatus monitor stopped.")

if __name__ == "__main__":
    main()
