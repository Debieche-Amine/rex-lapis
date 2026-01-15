import time
from RexLapisLib import Client, DataProcessor

# =================================================================
# CONFIGURATION
# =================================================================
SYMBOL = "XAUTUSDT"    # Must be XAUTUSDT for Spot
API_KEY = "q0xnzgz3YlKQNMy0OY"
API_SECRET = "y4fiS4lCnKqTdy6YmIslDjQwhDC7tGRSYf2p"
ENVIRONMENT = "demo"
CATEGORY = "spot"      # Required for XAUT
STORAGE_PATH = "./data" 

def run_comprehensive_data_test():
    # 1. Initialize Client for Spot
    client = Client(
        symbol=SYMBOL, 
        api_key=API_KEY, 
        api_secret=API_SECRET, 
        category=CATEGORY, 
        api_endpoint="mainnet" # Use mainnet for actual XAUT data
    )
    
    # 2. Initialize Processor with mandatory directory
    processor = DataProcessor(symbol=SYMBOL, storage_dir=STORAGE_PATH)

    print(f"\n--- Fetching {SYMBOL} Spot Data ---")

    # 3. Fetch Last 48 Hours
    start_ts = int((time.time() - (48 * 60 * 60)) * 1000)
    historical_df = client.get_historical_klines(interval="1", start_time_ms=start_ts)
    
    # 4. Save and Verify
    processor.save_to_csv(historical_df)
    print(f"Download complete. Total candles: {len(historical_df)}")

if __name__ == "__main__":
    run_comprehensive_data_test()