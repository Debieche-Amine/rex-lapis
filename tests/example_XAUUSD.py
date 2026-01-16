import time
import os
from RexLapisLib import Client, DataProcessor

# =================================================================
# CONFIGURATION
# =================================================================
SYMBOL = "XAUTUSDT"     
API_KEY = "q0xnzgz3YlKQNMy0OY"
API_SECRET = "y4fiS4lCnKqTdy6YmIslDjQwhDC7tGRSYf2p"
CATEGORY = "spot"       
STORAGE_PATH = "./data" 
INTERVAL = "1"          

def run_continuous_stream():
    client = Client(
        symbol=SYMBOL, 
        api_key=API_KEY, 
        api_secret=API_SECRET, 
        category=CATEGORY, 
        api_endpoint="mainnet" 
    )
    processor = DataProcessor(symbol=SYMBOL, storage_dir=STORAGE_PATH)

    print(f"--- Starting Continuous Stream for {SYMBOL} ---")
    
    try:
        while True:
            existing_data = processor.load_local_data()
            if not existing_data.empty:
                last_ts = int(existing_data['timestamp'].max().timestamp() * 1000)
                print(f"[*] Resuming from last timestamp: {existing_data['timestamp'].max()}")
            else:
                last_ts = int((time.time() - (24 * 60 * 60)) * 1000)
                print("[!] No local data found. Starting from last 24 hours.")

            try:
                new_data = client.get_historical_klines(
                    interval=INTERVAL, 
                    start_time_ms=last_ts
                )

                if not new_data.empty:
                    processor.save_to_csv(new_data)
                    print(f"[+] Synced {len(new_data)} new candles.")
                else:
                    print("[.] Up to date. Waiting for new candle...")

            except Exception as e:
                print(f"[!] Error during fetch: {e}")

            time.sleep(30)

    except KeyboardInterrupt:
        print("\n[!] Stream stopped by user. Saving and exiting...")

if __name__ == "__main__":
    run_continuous_stream()