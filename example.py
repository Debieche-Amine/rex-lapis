from client import Client

# 1. Initialize (binds to a specific symbol)
client = Client("BTCUSDT")

# 2. Setup Account (Auto-switches to Isolated Margin & sets Leverage)
client.setup_bot(leverage=5)

# 3. Get Data
price = client.get_current_price()
balance = client.get_usdt_balance()

# Get recent candles (Intervals: "1", "5", "15", "60", "D")
candles = client.get_candles(interval="60", limit=5)
last_close = candles[-1]['close']

print(f"Price: ${price} | Balance: ${balance} | Last Close: ${last_close}")

# 4. Place Orders (Returns Order ID string)
# Note: Inputs are automatically rounded to the correct precision.

# Limit Buy (Maker)
buy_id = client.place_limit_order(
    side="Buy", 
    qty=0.01, 
    price=60000.50, 
    post_only=True  # Guarantees Maker fee (cancels if Taker)
)

# Market Close (Reduce Only)
sell_id = client.place_market_order(
    side="Sell", 
    qty=0.01, 
    reduce_only=True # Ensures we don't flip position
)

print(f"Buy ID: {buy_id} | Sell ID: {sell_id}")
