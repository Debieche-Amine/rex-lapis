import time
from client import Client

def run_example_bot():
    print("--- 🤖 STARTING BYBIT BOT DEMO ---")
    
    # 1. INITIALIZATION
    # We bind the client to BTCUSDT immediately.
    symbol = "BTCUSDT"
    client = Client(symbol)
    print(f"✅ Client initialized for {symbol}")

    if not client.testnet:
        print("Exiting as a security precaution. This example should only be run on the testnet. Edit the code to allow this if you are certain.")
        exit()

    # 2. CHECK WALLET
    balance = client.get_usdt_balance()
    print(f"💰 USDT Balance: ${balance:.2f}")
    
    if balance < 10:
        print("❌ Balance too low to run demo safely.")
        return

    # 3. SETUP (Leverage & Margin)
    # This ensures we are in Isolated mode with 5x leverage.
    print("\n--- ⚙️ SETUP ---")
    client.setup_bot(leverage=5)

    # 4. MARKET ANALYSIS
    print("\n--- 📊 MARKET DATA ---")
    
    # Get current price
    current_price = client.get_current_price()
    print(f"Current Price: ${current_price}")

    # Get recent candles (last 5 hours) to see trend
    candles = client.get_candles(interval="60", limit=5)
    last_candle = candles[-1]
    print(f"Last Candle Close: ${last_candle['close']} (Vol: {last_candle['volume']})")

    # 5. EXECUTION: ENTER LONG POSITION
    # Let's open a small Long position using a Market Order
    print("\n--- 🚀 ENTERING POSITION ---")
    qty_to_buy = 0.005 # BTC
    
    try:
        client.place_market_order(side="Buy", qty=qty_to_buy)
        print("✅ Market Buy Order Sent")
    except Exception as e:
        print(f"❌ Failed to enter: {e}")
        return

    # Wait a moment for exchange to process
    time.sleep(2)

    # 6. VERIFY POSITION
    print("\n--- 🕵️ CHECKING POSITION ---")
    position = client.get_open_position()
    
    if position:
        entry_price = position['entry_price']
        size = position['size']
        print(f"✅ Position Open: {size} BTC @ ${entry_price}")
        print(f"   Unrealized PnL: {position['unrealized_pnl']} USDT")
        
        # 7. STRATEGY: PLACE TAKE PROFIT
        # We want to sell if price goes up 1%
        # IMPORTANT: reduce_only=True ensures this order closes the position 
        # and doesn't flip it into a Short if we accidentally double click.
        
        target_price = entry_price * 1.01 
        print(f"\n--- 🎯 PLACING TAKE PROFIT @ ${target_price:.2f} ---")
        
        try:
            client.place_limit_order(
                side="Sell", 
                qty=size, 
                price=target_price, 
                reduce_only=True
            )
            print("✅ Take Profit Limit Order Placed")
        except Exception as e:
            print(f"❌ Failed to set TP: {e}")
            
    else:
        print("⚠️ No position found (Order might not have filled yet?)")

    # 8. MONITORING OPEN ORDERS
    print("\n--- 📋 OPEN ORDERS ---")
    open_orders = client.get_open_orders()
    for o in open_orders:
        print(f" 🔹 {o['side']} {o['type']}: {o['qty']} @ ${o['price']} (Status: {o['status']})")

    # 9. CLEANUP (Optional for Demo)
    # Cancel the TP order we just made, just to show how it's done.
    print("\n--- 🧹 CLEANUP (Canceling Orders) ---")
    time.sleep(2)
    client.cancel_all_orders()
    print("✅ All open orders canceled.")

    # Close the position (Market Sell remaining size)
    if position:
        print("🔻 Closing position via Market...")
        client.place_market_order(side="Sell", qty=position['size'], reduce_only=True)
        print("✅ Position Closed.")

    print("\n--- 🏁 DEMO COMPLETE ---")

if __name__ == "__main__":
    run_example_bot()
