import time
from RexLapisLib import Client, DataProcessor

# =================================================================
# CONFIGURATION
# =================================================================
SYMBOL = "BTCUSDT"
API_KEY = "q0xnzgz3YlKQNMy0OY"
API_SECRET = "y4fiS4lCnKqTdy6YmIslDjQwhDC7tGRSYf2p"
ENVIRONMENT = "demo"
# NEW: Define exactly where you want to save the data
STORAGE_PATH = "./data" 

def run_comprehensive_data_test():
    # 1. Initialize Client
    client = Client(symbol=SYMBOL, api_key=API_KEY, api_secret=API_SECRET, api_endpoint=ENVIRONMENT)
    
    # 2. Initialize DataProcessor with the required storage_dir
    # The file will be saved as: ./data/BTCUSDT_history.csv
    processor = DataProcessor(symbol=SYMBOL, storage_dir=STORAGE_PATH)

    print(f"\n{'='*50}")
    print(f"STARTING COMPREHENSIVE DATA TEST FOR {SYMBOL}")
    print(f"{'='*50}\n")

    # 3. Market Data Test
    price = client.get_current_price()
    print(f"Current Price: ${price}")

    # 4. Long-term Historical Data (Last 48 Hours)
    start_ts = int((time.time() - (48 * 60 * 60)) * 1000)
    historical_df = client.get_historical_klines(interval="1", start_time_ms=start_ts)
    
    # 5. Save to CSV (Deduplication check)
    processor.save_to_csv(historical_df)
    
    # 6. Verification
    local_data = processor.load_local_data()
    print(f"Success! Local CSV in '{STORAGE_PATH}' contains {len(local_data)} records.")

if __name__ == "__main__":
    run_comprehensive_data_test()