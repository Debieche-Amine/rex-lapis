import sys
import os
import time
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from RexLapisLib import Client, LiveContext, TechnicalEngine
from RexLapisLib.core.manager import TradeManager  
from strategies.pro_features_test_strategy import ProFeaturesTestStrategy

# Load API Keys from .env file
load_dotenv()

def main():
    print("--- Starting RexLapis LIVE TRADING Engine (Fault-Tolerant Version) ---")
    
    # 1. Configuration
    SYMBOL = "XAUTUSDT"
    TIMEFRAME = "1"  # 1-minute interval
    STATE_FILE = "bot_memory.json" # Memory file to survive power cuts
    
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")
    IS_TESTNET = True 

    if not API_KEY or not API_SECRET:
        print("Error: API Keys not found in .env file.")
        return

    # 2. Initialize Core Components
    client = Client(
        symbol=SYMBOL, 
        api_key=API_KEY, 
        api_secret=API_SECRET, 
        category="spot", 
        api_endpoint="demo" if IS_TESTNET else "mainnet"
    )

    context = LiveContext(client)
    strategy = ProFeaturesTestStrategy()
    strategy.setup(context)
    tech_engine = TechnicalEngine()

    # --- POWER RECOVERY LOGIC ---
    # This part runs once when the bot starts/restarts after a crash
    manager = TradeManager(client, state_file=STATE_FILE)
    print("🔍 Checking for previous state after restart...")
    recovered_state = manager.reconcile_after_crash()
    
    if recovered_state:
        print(f"✅ Recovery Successful. Resuming management of active trade.")
    else:
        print("ℹ️ No previous active trades found. Starting fresh.")

    print(f"Bot initialized for {SYMBOL}. Waiting for next candle...")

    last_processed_timestamp = None 

    # 3. Live Trading Loop (Network-Resilient)
    while True:
        try:
            # A. Fetch candles (Handled by @auto_resync inside Client)
            # If internet is down, this call will freeze and retry automatically
            candles_data = client.get_candles(interval=TIMEFRAME, limit=200)
            
            if not candles_data:
                time.sleep(5)
                continue

            # Convert and process data
            df = pd.DataFrame(candles_data)
            df['timestamp'] = pd.to_datetime(df['start_time'].astype(float), unit='ms')
            df.sort_values('timestamp', inplace=True)
            df = tech_engine.apply_all_indicators(df)

            # Get the current candle timestamp
            current_candle_timestamp = df.iloc[-1]['timestamp']

            # B. Execute Strategy Logic on New Candle
            if current_candle_timestamp != last_processed_timestamp:
                print(f"\n[NEW CANDLE] {current_candle_timestamp} | Price: {df.iloc[-1]['close']}")
                
                # Run strategy tick
                strategy.on_candle_tick(df)
                
                # --- AUTO-SAVE LOGIC ---
                # Immediately save the bot's mind to disk to survive power cuts
                state_to_save = {
                    "last_processed_time": str(current_candle_timestamp),
                    "position": strategy.position,
                    "balance": context.get_balance()
                }
                manager.save_state(state_to_save)
                
                last_processed_timestamp = current_candle_timestamp

            else:
                # Still in the same minute, show heartbeat
                print(".", end="", flush=True) 
            
            # Polling delay
            time.sleep(10) 

        except KeyboardInterrupt:
            print("\n--- Stopping Live Engine Safely ---")
            break
        except Exception as e:
            # Final safety net for unexpected software bugs
            print(f"\n🚨 [CRITICAL ERROR]: {e}")
            print("Attempting to stay alive. Cooling down for 30s...")
            time.sleep(30)

if __name__ == "__main__":
    main()