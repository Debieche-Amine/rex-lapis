```md
bybit_client_documentation.md
```

# Bybit API V5 Client Class Documentation

The `Client` class serves as the primary interface between your trading strategy and the Bybit platform. It is designed to abstract away the complexities of the Bybit API (Version 5), providing a streamlined way to manage balances, fetch market data, and execute orders with precision.

## Key Features

*   **Multi-Category Support:** Works seamlessly with both Spot and Linear Futures trading.
*   **Precision Handling:** Automatically rounds prices and quantities according to Bybit's specific requirements for each symbol.
*   **Safe Trading System:** Supports "Post-Only" orders to ensure you benefit from maker fees.
*   **Data Synchronization:** Includes features for fetching historical data with automatic pagination to ensure no data is missed.
*   **Real-time Streaming:** Supports WebSocket for receiving real-time candle data.

## Initialization

To begin, you need to instantiate the `Client` class, providing your Bybit API credentials.

```python
from RexLapisLib import Client

client = Client(
    symbol="BTCUSDT",
    api_key="YOUR_API_KEY",
    api_secret="YOUR_API_SECRET",
    category="linear",   # Options: "spot" or "linear"
    api_endpoint="demo"  # Options: "demo" for Testnet or "live" for Mainnet
)
```

### Parameters

| Parameter    | Type   | Description                                      |
| :----------- | :----- | :----------------------------------------------- |
3. `symbol`    | `str`  | The trading pair (e.g., "ETHUSDT").              |
4. `api_key`   | `str`  | Your Bybit API Key.                              |
5. `api_secret`| `str`  | Your Bybit API Secret Key.                       |
6. `category`  | `str`  | Trading category: `linear` for futures, `spot` for spot. |
7. `api_endpoint` | `str`  | Environment: `demo` (Testnet) or `live` (Mainnet). |

## Market Data

### Get Current Price

Retrieves the last traded price for the specified symbol.

```python
price = client.get_current_price()
```

### Get Candles (Klines)

Fetches a list of recent candles (defaults to 200 candles).

```python
candles = client.get_candles(interval="15", limit=100)
```

### Synchronize Historical Data

A robust function for fetching large amounts of historical data with automatic pagination.

```python
historical_df = client.get_historical_klines(
    interval="1",
    start_time_ms=1672531200000 # Timestamp in milliseconds
)
```

## Account & Positions Management

### Check Balance

Returns the available USDT balance in the unified account.

```python
balance = client.get_usdt_balance()
```

### Get Open Position

Returns details of the current open position (size, entry price, unrealized P/L), or `None` if no position is open.

```python
position = client.get_open_position()
if position:
    print(f"Entry Price: {position['entry_price']}")
```

## Order Execution

### Setup Account (for Futures)

Configures the account to "Isolated" margin mode and sets the leverage.

```python
client.setup_bot(leverage=10)
```

### Place Limit Order

Automatically rounds quantity and price according to platform requirements.

```python
order_id = client.place_limit_order(
    side="Buy",
    qty=0.01,
    price=25000.5,
    post_only=True # Ensures the order does not execute immediately as a Taker
)
```

### Place Market Order

```python
order_id = client.place_market_order(side="Sell", qty=0.02)
```

## Real-time Streaming (WebSocket)

You can enable a live stream to receive new candles as soon as they close, feeding them directly into your strategy.

```python
def my_callback(candle_data):
    print(f"New Candle: {candle_data['close']}")

client.start_kline_stream(callback=my_callback, interval="1")
```

## Important Notes

*   **Error Handling:** The class is designed to ignore certain common Bybit errors (e.g., attempting to set leverage that is already set) to prevent bot downtime.
*   **Security:** Ensure your `api_key` and `api_secret` are stored securely (e.g., in a `.env` file) and not hardcoded directly into your script.