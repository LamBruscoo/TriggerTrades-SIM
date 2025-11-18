#!/usr/bin/env python3
"""
Reset Trading Day - Python Helper Script
Programmatically trigger zero-out and fresh start
"""
import sys
import time
import json
import pathlib
from typing import Optional

class TradingResetController:
    """Controller for managing trading day resets"""
    
    def __init__(self, runtime_dir: str = "runtime"):
        self.runtime = pathlib.Path(runtime_dir)
        self.reset_request = self.runtime / "reset.request"
        self.state_file = self.runtime / "state.json"
        self.trades_file = self.runtime / "trades.jsonl"
    
    def get_current_state(self) -> Optional[dict]:
        """Read current strategy state"""
        try:
            return json.loads(self.state_file.read_text())
        except Exception as e:
            print(f"Warning: Could not read state: {e}")
            return None
    
    def get_current_position(self) -> Optional[int]:
        """Calculate current position from trades log"""
        try:
            position = 0
            with self.trades_file.open("r") as f:
                for line in f:
                    trade = json.loads(line.strip())
                    qty = trade.get("qty", 0)
                    side = trade.get("side", "")
                    if side == "BUY":
                        position += qty
                    elif side == "SELL":
                        position -= qty
            return position
        except Exception as e:
            print(f"Warning: Could not calculate position: {e}")
            return None
    
    def trigger_reset(self, confirm: bool = True) -> bool:
        """Trigger the reset sequence"""
        if confirm:
            state = self.get_current_state()
            position = self.get_current_position()
            
            print("═" * 60)
            print("ZERO OUT & RESET TRADING DAY")
            print("═" * 60)
            
            if state:
                print(f"Current Phase: {state.get('phase', 'UNKNOWN')}")
                print(f"Last Price: ${state.get('last_price', 0.0):.2f}")
                print(f"Base Price: ${state.get('base_price', 0.0):.2f}")
                print(f"Cycles: {state.get('cycles', 0)}")
            
            if position is not None:
                print(f"Current Position: {position:+d} shares")
            
            print("\nThis will:")
            print("  1. Flatten all positions to ZERO")
            print("  2. Reset strategy state to IDLE")
            print("  3. Reset daily PnL tracking")
            print("  4. Resume trading immediately")
            
            response = input("\nProceed with reset? (yes/no): ").strip().lower()
            if response != "yes":
                print("Reset cancelled.")
                return False
        
        try:
            self.runtime.mkdir(exist_ok=True)
            self.reset_request.write_text("reset")
            print("\n✓ Reset request submitted successfully!")
            print("  → Check system logs for confirmation")
            print("  → Position will flatten within 1-2 seconds")
            return True
        except Exception as e:
            print(f"\n✗ Failed to submit reset request: {e}")
            return False
    
    def wait_for_reset_completion(self, timeout: int = 10) -> bool:
        """Wait for reset to complete (request file removed)"""
        print("\nWaiting for reset completion...", end="", flush=True)
        start = time.time()
        
        while time.time() - start < timeout:
            if not self.reset_request.exists():
                print(" ✓ Complete!")
                return True
            print(".", end="", flush=True)
            time.sleep(0.5)
        
        print(" ✗ Timeout")
        return False
    
    def verify_reset(self) -> bool:
        """Verify reset was successful"""
        state = self.get_current_state()
        if not state:
            return False
        
        phase = state.get("phase", "")
        is_idle = phase in ("IDLE", "T1_WINDOW")
        
        print("\nReset Verification:")
        print(f"  Phase: {phase} {'✓' if is_idle else '✗'}")
        print(f"  Ready for Trading: {'YES' if is_idle else 'NO'}")
        
        return is_idle


def main():
    """CLI interface for reset controller"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Zero out positions and reset trading day",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive reset (with confirmation)
  python reset_trading.py
  
  # Auto-confirm reset
  python reset_trading.py --yes
  
  # Reset and wait for completion
  python reset_trading.py --yes --wait
  
  # Check current status only
  python reset_trading.py --status
        """
    )
    
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    parser.add_argument(
        "--wait", "-w",
        action="store_true",
        help="Wait for reset to complete"
    )
    
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show current status only (no reset)"
    )
    
    parser.add_argument(
        "--runtime",
        default="runtime",
        help="Path to runtime directory (default: runtime)"
    )
    
    args = parser.parse_args()
    
    controller = TradingResetController(runtime_dir=args.runtime)
    
    # Status only mode
    if args.status:
        state = controller.get_current_state()
        position = controller.get_current_position()
        
        print("═" * 60)
        print("CURRENT TRADING STATUS")
        print("═" * 60)
        
        if state:
            print(f"Phase: {state.get('phase', 'UNKNOWN')}")
            print(f"Last Price: ${state.get('last_price', 0.0):.2f}")
            print(f"Base Price: ${state.get('base_price', 0.0):.2f}")
            print(f"Cycles: {state.get('cycles', 0)}")
            print(f"Mode: {state.get('mode', 'unknown')}")
        else:
            print("State: UNAVAILABLE")
        
        if position is not None:
            print(f"\nCurrent Position: {position:+d} shares")
        
        sys.exit(0)
    
    # Trigger reset
    success = controller.trigger_reset(confirm=not args.yes)
    
    if not success:
        sys.exit(1)
    
    # Wait if requested
    if args.wait:
        if controller.wait_for_reset_completion():
            controller.verify_reset()
        else:
            print("\nWarning: Reset may still be processing")
            sys.exit(1)


if __name__ == "__main__":
    main()
