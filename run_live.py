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
from strategies.advanced_rsi import AdvancedRSIStrategy

# Load API Keys from .env file
load_dotenv()

def main():
    print("--- Starting RexLapis LIVE TRADING Engine ---")
    
    # 1. Configuration
    SYMBOL = "XAUTUSDT"
    TIMEFRAME = "1"  # 1-minute interval
    API_KEY = os.getenv("BYBIT_API_KEY")
    API_SECRET = os.getenv("BYBIT_API_SECRET")
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
    strategy = AdvancedRSIStrategy()
    strategy.setup(context)
    
    # Initialize Technical Engine (for calculating RSI, etc.)
    tech_engine = TechnicalEngine()

    print(f"Bot initialized for {SYMBOL}. Waiting for next candle...")

    # 3. Live Trading Loop (Polling Mechanism)
    try:
        while True:
            # A. Fetch the latest 200 candles (enough for indicators)
            # Note: We use the client to get fresh data
            candles_data = client.get_candles(interval=TIMEFRAME, limit=200)
            
            if not candles_data:
                print("Warning: Failed to fetch candles. Retrying...")
                time.sleep(5)
                continue

            # Convert to DataFrame
            df = pd.DataFrame(candles_data)
            df['timestamp'] = pd.to_datetime(df['start_time'].astype(float), unit='ms')
            df.sort_values('timestamp', inplace=True)

            # B. Apply Technical Indicators (Calculates RSI, MA, etc.)
            df = tech_engine.apply_all_indicators(df)

            # C. Execute Strategy Logic
            # We pass the full DataFrame. The strategy looks at the last row.
            strategy.on_candle_tick(df)

            # D. Wait for the next cycle
            # For a 1-minute timeframe, we sleep for a bit to avoid spamming API
            print(f"[{pd.Timestamp.now()}] Tick processed. Close: {df.iloc[-1]['close']}")
            time.sleep(10) # Check every 10 seconds

    except KeyboardInterrupt:
        print("\n--- Stopping Live Engine ---")

if __name__ == "__main__":
    main()