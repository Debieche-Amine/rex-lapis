# Rex Lapis
Rex Lapis, Morax the Geo Archon, is the god who built Liyue on unbreakable contracts and trade.
Every agreement under his rule was absolute, forging trust, commerce, and prosperity across the land.
Now as Zhongli, he embodies the belief that a contract—once made—must always be honored.


## 0. Gold prediction
Slope (a): 0.001012899940494811
Intercept (b): 7.586419247136773

gold(t) = exp(b)*exp(a*t)
where t is the number of days from 2024-1-1


## 1. Setup

```bash
pip install -r requirements.txt
```

Create a .env with
```bash
API_KEY=
API_SECRET=
API_ENDPOINT=demo # or testnet or mainnet
```
API_TEST determine where to connect:
- testnet is found on <https://testnet.bybit.com>,
- mainnet is the normal <https://www.bybit.com>,
- demo is accessed normally from mainnet, then going to demo trading, The Api endpoint is: <https://api-demo.bybit.com>


## 2. Quick Start Example
Check <./docs/client.md> for a more detailed documentation

```python
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
```
