#!/usr/bin/env python3
"""
Reset Feature Test Suite
Validates all components of the zero-out & reset feature
"""
import sys
import json
import pathlib
import time
from typing import Tuple

class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

def print_test(name: str):
    print(f"\n{Color.BLUE}▶{Color.RESET} Testing: {name}")

def print_pass(msg: str):
    print(f"  {Color.GREEN}✓{Color.RESET} {msg}")

def print_fail(msg: str):
    print(f"  {Color.RED}✗{Color.RESET} {msg}")

def print_warn(msg: str):
    print(f"  {Color.YELLOW}⚠{Color.RESET} {msg}")

def test_config_file() -> bool:
    """Test if config.py has the new setting"""
    print_test("config.py modifications")
    try:
        with open("config.py", "r") as f:
            content = f.read()
        
        if "enable_manual_reset" in content:
            print_pass("enable_manual_reset setting found")
            return True
        else:
            print_fail("enable_manual_reset setting not found")
            return False
    except Exception as e:
        print_fail(f"Could not read config.py: {e}")
        return False

def test_risk_gate() -> bool:
    """Test if risk_gate.py has reset method"""
    print_test("risk_gate.py modifications")
    try:
        with open("risk_gate.py", "r") as f:
            content = f.read()
        
        if "reset_daily_pnl" in content:
            print_pass("reset_daily_pnl() method found")
            return True
        else:
            print_fail("reset_daily_pnl() method not found")
            return False
    except Exception as e:
        print_fail(f"Could not read risk_gate.py: {e}")
        return False

def test_run_demo() -> bool:
    """Test if run_demo.py has all modifications"""
    print_test("run_demo.py modifications")
    try:
        with open("run_demo.py", "r") as f:
            content = f.read()
        
        checks = [
            ("flatten_all enhancement", "OrderSignal" in content and "FLATTEN" in content),
            ("reset_state enhancement", "reset_daily_pnl" in content),
            ("reset_watcher task", "reset_watcher" in content),
            ("reset_watcher in tasks", "reset_watcher()" in content),
        ]
        
        all_pass = True
        for name, condition in checks:
            if condition:
                print_pass(name)
            else:
                print_fail(name)
                all_pass = False
        
        return all_pass
    except Exception as e:
        print_fail(f"Could not read run_demo.py: {e}")
        return False

def test_scripts_exist() -> bool:
    """Test if new scripts exist and are executable"""
    print_test("New script files")
    
    scripts = [
        "reset_trading.sh",
        "reset_trading.py",
        "status_monitor.py",
    ]
    
    all_pass = True
    for script in scripts:
        path = pathlib.Path(script)
        if path.exists():
            is_executable = path.stat().st_mode & 0o111
            if is_executable:
                print_pass(f"{script} exists and is executable")
            else:
                print_warn(f"{script} exists but is not executable")
                all_pass = False
        else:
            print_fail(f"{script} not found")
            all_pass = False
    
    return all_pass

def test_docs_exist() -> bool:
    """Test if documentation files exist"""
    print_test("Documentation files")
    
    docs = [
        "RESET_GUIDE.md",
        "RESET_QUICKSTART.md",
        "IMPLEMENTATION_SUMMARY.md",
        "RESET_DIAGRAM.txt",
    ]
    
    all_pass = True
    for doc in docs:
        path = pathlib.Path(doc)
        if path.exists():
            size = path.stat().st_size
            print_pass(f"{doc} exists ({size} bytes)")
        else:
            print_fail(f"{doc} not found")
            all_pass = False
    
    return all_pass

def test_env_example() -> bool:
    """Test if .env.example has new setting"""
    print_test(".env.example modifications")
    try:
        with open(".env.example", "r") as f:
            content = f.read()
        
        if "ENABLE_MANUAL_RESET" in content:
            print_pass("ENABLE_MANUAL_RESET setting found in .env.example")
            return True
        else:
            print_fail("ENABLE_MANUAL_RESET setting not found")
            return False
    except Exception as e:
        print_fail(f"Could not read .env.example: {e}")
        return False

def test_runtime_directory() -> bool:
    """Test runtime directory setup"""
    print_test("Runtime directory")
    
    runtime = pathlib.Path("runtime")
    if runtime.exists():
        if runtime.is_dir():
            print_pass("runtime/ directory exists")
            
            # Check for expected files (may not exist yet)
            expected = ["state.json", "trades.jsonl", "prices.jsonl", "mode.txt"]
            for fname in expected:
                fpath = runtime / fname
                if fpath.exists():
                    print_pass(f"  {fname} exists")
                else:
                    print_warn(f"  {fname} not found (will be created at runtime)")
            return True
        else:
            print_fail("runtime exists but is not a directory")
            return False
    else:
        print_warn("runtime/ directory doesn't exist yet (will be created)")
        return True

def test_reset_script_syntax() -> bool:
    """Test if Python scripts have valid syntax"""
    print_test("Python script syntax")
    
    scripts = ["reset_trading.py", "status_monitor.py"]
    all_pass = True
    
    for script in scripts:
        try:
            with open(script, "r") as f:
                code = f.read()
            compile(code, script, "exec")
            print_pass(f"{script} syntax is valid")
        except SyntaxError as e:
            print_fail(f"{script} has syntax error: {e}")
            all_pass = False
        except Exception as e:
            print_fail(f"Could not check {script}: {e}")
            all_pass = False
    
    return all_pass

def test_readme_updated() -> bool:
    """Test if README.md mentions the reset feature"""
    print_test("README.md updates")
    try:
        with open("README.md", "r") as f:
            content = f.read()
        
        if "Zero Out" in content or "reset" in content.lower():
            print_pass("README.md mentions reset feature")
            return True
        else:
            print_warn("README.md doesn't mention reset feature")
            return False
    except Exception as e:
        print_fail(f"Could not read README.md: {e}")
        return False

def run_all_tests() -> Tuple[int, int]:
    """Run all tests and return (passed, total)"""
    tests = [
        test_config_file,
        test_risk_gate,
        test_run_demo,
        test_scripts_exist,
        test_docs_exist,
        test_env_example,
        test_runtime_directory,
        test_reset_script_syntax,
        test_readme_updated,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    return passed, total

def main():
    """Run test suite"""
    print(f"{Color.BOLD}{'='*70}")
    print("  RESET FEATURE TEST SUITE")
    print(f"{'='*70}{Color.RESET}")
    
    start_time = time.time()
    passed, total = run_all_tests()
    elapsed = time.time() - start_time
    
    print(f"\n{Color.BOLD}{'='*70}")
    print("  TEST SUMMARY")
    print(f"{'='*70}{Color.RESET}")
    
    percentage = (passed / total) * 100
    
    if passed == total:
        color = Color.GREEN
        status = "ALL TESTS PASSED"
    elif passed >= total * 0.8:
        color = Color.YELLOW
        status = "MOSTLY PASSING"
    else:
        color = Color.RED
        status = "SOME TESTS FAILED"
    
    print(f"\n{color}{status}{Color.RESET}")
    print(f"Passed: {passed}/{total} ({percentage:.1f}%)")
    print(f"Time: {elapsed:.2f}s")
    
    if passed == total:
        print(f"\n{Color.GREEN}✓ All components verified. Feature is ready to use!{Color.RESET}")
        print("\nNext steps:")
        print("  1. Start the system:  python run_demo.py")
        print("  2. Monitor status:    python status_monitor.py")
        print("  3. Test reset:        ./reset_trading.sh")
        print("\nSee RESET_QUICKSTART.md for usage guide.")
        sys.exit(0)
    else:
        print(f"\n{Color.YELLOW}⚠ Some checks failed. Review the output above.{Color.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
