import sys
import os
import time
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from RexLapisLib import Client
from RexLapisLib import LiveContext
from RexLapisLib import TechnicalEngine
from strategies.pro_features_test_strategy import ProFeaturesTestStrategy

# Load API Keys from .env file
load_dotenv()

def main():
    print("--- Starting RexLapis LIVE TRADING Engine ---")
    
    # 1. Configuration
    SYMBOL = "XAUTUSDT"
    TIMEFRAME = "1"  # 1-minute interval
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    IS_TESTNET = True # Set to False for Real Money

    if not API_KEY or not API_SECRET:
        print("Error: API Keys not found in .env file.")
        return

    # 2. Initialize Components
    # Connect to Bybit
    client = Client(
        symbol=SYMBOL, 
        api_key=API_KEY, 
        api_secret=API_SECRET, 
        category="spot", 
        api_endpoint="demo" if IS_TESTNET else "mainnet"
    )

    # Create the Live Context (The Bridge)
    context = LiveContext(client)
    
    # Initialize the Strategy and link it to the Live Context
    strategy = ProFeaturesTestStrategy()
    strategy.setup(context)
    
    # Initialize Technical Engine
    tech_engine = TechnicalEngine()

    print(f"Bot initialized for {SYMBOL}. Waiting for next candle...")

    # --- VARIABLE TO TRACK THE LAST PROCESSED CANDLE ---
    last_processed_timestamp = None 

    # 3. Live Trading Loop (Polling Mechanism)
    try:
        while True:
            try:
                # A. Fetch the latest 200 candles
                candles_data = client.get_candles(interval=TIMEFRAME, limit=200)
                
                if not candles_data:
                    print("Warning: Failed to fetch candles. Retrying...")
                    time.sleep(5)
                    continue

                # Convert to DataFrame
                df = pd.DataFrame(candles_data)
                df['timestamp'] = pd.to_datetime(df['start_time'].astype(float), unit='ms')
                df.sort_values('timestamp', inplace=True)

                # B. Apply Indicators
                df = tech_engine.apply_all_indicators(df)

                # --- CRITICAL FIX HERE ---
                # Get the timestamp of the newest candle
                current_candle_timestamp = df.iloc[-1]['timestamp']

                # Check if this timestamp is different from the last one we processed
                if current_candle_timestamp != last_processed_timestamp:
                    
                    print(f"\n[NEW CANDLE DETECTED] {current_candle_timestamp}")
                    
                    # C. Execute Strategy (Only once per new candle)
                    strategy.on_candle_tick(df)
                    
                    # Update the tracker
                    last_processed_timestamp = current_candle_timestamp
                    
                    # Optional: Print current close price
                    print(f"Processed Close Price: {df.iloc[-1]['close']}")

                else:
                    # We are still in the same minute, do nothing
                    print(f".", end="", flush=True) # Print a dot to show it's alive
                
                # -------------------------
                
                # Sleep to avoid API spamming
                time.sleep(10) 

            except Exception as e:
                # Catch API errors (like timestamp sync issues) without stopping the bot
                print(f"\n⚠️ An error occurred: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)

    except KeyboardInterrupt:
        print("\n--- Stopping Live Engine ---")

if __name__ == "__main__":
    main()