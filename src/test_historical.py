# src/test_historical.py - FIXED for running from src/ folder
import sys
import os

print("=== Testing from src/ folder ===")
print(f"Current directory: {os.getcwd()}")

# Add parent directory to path for .env loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now imports should work since we're already in src/
try:
    from main import UrbanTrafficSystem
    print("✓ Import successful")
    
    # Initialize system
    print("\nInitializing system...")
    system = UrbanTrafficSystem()
    
    # Test 1: Quick forecast
    print("\n" + "="*50)
    print("TEST 1: Quick Forecast")
    print("="*50)
    system.quick_forecast()
    
    # Test 2: Historical analysis
    print("\n" + "="*50)
    print("TEST 2: Colombo → Kandy")
    print("="*50)
    system.analyze_with_history("Colombo, Sri Lanka", "Kandy, Sri Lanka")
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    print("\nDebug info:")
    print(f"sys.path: {sys.path}")
    print(f"Files in current dir: {os.listdir('.')}")