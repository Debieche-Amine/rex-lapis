# Bybit Client Wrapper Documentation

This project uses a custom wrapper around `pybit.unified_trading` designed specifically for **Linear USDT Perpetual Futures**.

It abstracts away API complexity, handles mathematical precision automatically, and enforces **Isolated Margin** for safety.

## 📋 Prerequisites

The client relies on a `.env` file in the root directory for authentication:

```env
API_KEY=your_api_key_here
API_SECRET=your_api_secret_here
API_ENDPOINT=demo # or testnet or mainnet
```

## 🚀 Initialization

The client is bound to a single trading pair (Symbol) upon instantiation. It immediately fetches instrument info (tick size, lot size) to ensure all subsequent calculations are precise.

```python
from client import Client

# Initialize for Bitcoin
client = Client("BTCUSDT")
```

---

## ⚙️ Setup Methods

### `setup_bot(leverage: int)`
Configures the account for the specific symbol.
1.  Switches the margin mode to **Isolated**.
2.  Sets the requested **Leverage**.

*Note: This method suppresses "not modified" errors from Bybit (e.g., if leverage is already correct), keeping logs clean.*

```python
client.setup_bot(leverage=5)
```

---

## 📊 Market & Account Data

### `get_current_price() -> float`
Returns the latest traded price for the bound symbol.

### `get_usdt_balance() -> float`
Returns the available free margin (USDT) in the Unified Trading Account.

### `get_open_position()`
Returns a dictionary containing position details if a position exists (size > 0). Returns `None` if flat.

**Return Structure:**
```python
{
    "size": float,           # e.g., 0.5
    "side": str,             # "Buy" or "Sell"
    "entry_price": float,    # e.g., 65000.50
    "unrealized_pnl": float, # USDT PnL
    "leverage": str          # e.g., "10"
}
```

### `get_candles(interval: str, limit: int = 200)`
Fetches historical OHLCV data.
*   **interval:** `"1"`, `"5"`, `"15"`, `"60"` (1h), `"D"` (Daily).
*   **Returns:** A list of dictionaries ordered from **Oldest to Newest**.

### `get_open_orders()`
Fetches all active (unfilled) Limit or Conditional orders for the symbol.

**Return Structure:**
```python
[
    {
        "order_id": str,
        "price": float,
        "qty": float,
        "side": str,      # "Buy" or "Sell"
        "type": str,      # "Limit"
        "status": str     # "New" or "PartiallyFilled"
    },
    ...
]
```

---

## 🛠️ Trading Methods

### 🛡️ Automatic Precision Handling
All trading methods utilize internal helpers (`_round_qty` and `_round_price`) to sanitize inputs before sending them to Bybit.
*   **Quantity:** Always rounded **DOWN** to the nearest step size (prevents "Insufficient Margin").
*   **Price (Buy):** Rounded **DOWN** (Floor) to nearest tick.
*   **Price (Sell):** Rounded **UP** (Ceiling) to nearest tick.

### `place_limit_order(side, qty, price, reduce_only=False, post_only=False) -> str`
Places a standard Limit order.

*   `side`: `"Buy"` or `"Sell"`.
*   `qty`: Amount in coin (e.g., BTC).
*   `price`: Trigger price in USDT.
*   `reduce_only`: If `True`, guarantees the order will only close a position, never open a new one.
*   `post_only`: If `True`, sets timeInForce to **"PostOnly"**. The order will be rejected if it would fill immediately (guarantees Maker fees).
*   **Returns:** The Order ID as a `str`.

### `place_market_order(side, qty, reduce_only=False) -> str`
Places a Market order (Instant fill).

*   `side`: `"Buy"` or `"Sell"`.
*   `qty`: Amount in coin (e.g., BTC).
*   `reduce_only`: If `True`, guarantees the order will only close a position.
*   **Returns:** The Order ID as a `str`.

### `cancel_all_orders()`
Cancels **ALL** open orders for the bound symbol.

---

## 📝 Example Usage

```python
from client import Client

client = Client("ETHUSDT")

# 1. Setup
client.setup_bot(leverage=5)

# 2. Check Data
price = client.get_current_price()
print(f"ETH Price: {price}")

# 3. Enter Long
client.place_limit_order("Buy", qty=0.1, price=price - 10)

# 4. Check Orders
orders = client.get_open_orders()
print(f"Open Orders: {len(orders)}")
```
