import sys
import os
from dotenv import load_dotenv

# Add project root
sys.path.append(os.getcwd())

from RexLapisLib import BacktestEngine
from RexLapisLib import DataProcessor
from RexLapisLib import Client
from RexLapisLib import show_dashboard
from strategies.pro_features_test_strategy import ProFeaturesTestStrategy

# Load .env for API Keys (Needed to fetch data)
load_dotenv()

# ==========================================
# USER SETTINGS
# ==========================================
VISUALIZE = True         # Show Dashboard?
AUTO_UPDATE_DATA = True  # <--- NEW: Fetch fresh data before running?
SYMBOL = "XAUTUSDT"

def main():
    print(f"--- Starting RexLapis Simulation: {SYMBOL} ---")

    # 1. Initialize Data Processor
    processor = DataProcessor(symbol=SYMBOL, storage_dir="./data")

    # 2. AUTO-UPDATE LOGIC (Fetching fresh data)
    if AUTO_UPDATE_DATA:
        api_key = os.getenv("API_KEY")
        api_secret = os.getenv("API_SECRET")
        
        if api_key and api_secret:
            print("📡 Connecting to Bybit to check for new data...")
            try:
                # Initialize Client (Using Mainnet to get real history)
                client = Client(
                    symbol=SYMBOL, 
                    api_key=api_key, 
                    api_secret=api_secret, 
                    api_endpoint="mainnet" 
                )
                
                # Use the processor's sync logic
                # We assume processor has a method to sync. If not, we call it here.
                processor.sync_gap(client)
                print("✅ Data is up-to-date.")
                
            except Exception as e:
                print(f"⚠️ Warning: Could not update data. Using local file. Error: {e}")
        else:
            print("⚠️ Warning: API Keys not found in .env. Skipping auto-update.")

    # 3. Load Data (Now it's fresh)
    df = processor.load_local_data()

    if df.empty:
        print("❌ Error: No data found. Please place a CSV or enable AUTO_UPDATE_DATA with valid API keys.")
        return

    print(f"Loaded {len(df)} candles. Last candle: {df.iloc[-1]['timestamp']}")

    # 4. Run Strategy
    my_strategy = ProFeaturesTestStrategy()
    engine = BacktestEngine(strategy=my_strategy, initial_balance=10000)
    
    print("🚀 Running simulation...")
    results = engine.run(df)
    
    results['strategy_name'] = my_strategy.__class__.__name__

    # 5. Output
    if VISUALIZE:
        show_dashboard(results)
    else:
        print_text_report(results)

def print_text_report(results):
    print("\n" + "="*40)
    print("          SIMULATION REPORT           ")
    print("="*40)
    print(f"Initial Balance: ${results['initial_balance']:,.2f}")
    print(f"Final Balance:   ${results['final_balance']:,.2f}")
    print(f"ROI (Profit):    {results['roi']:.2f}%")
    print(f"Total Trades:    {results['total_trades']}")
    print("="*40)

if __name__ == "__main__":
    main()