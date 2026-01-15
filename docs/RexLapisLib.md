```md
rexlapis_documentation.md
```

# RexLapis Library Documentation

RexLapis is a high-level Python framework built on top of pybit (Bybit V5), designed for Linear USDT Perpetual Futures. It provides an automated trade lifecycle manager, historical data processing, and safe execution with precision handling.

## 📋 Table of Contents

*   [Prerequisites](#prerequisites)
*   [Core Components](#core-components)
    *   [The Client (Execution)](#the-client-execution)
    *   [Trade Manager (Orchestration)](#trade-manager-orchestration)
    *   [Data Processor (Storage & Analysis)](#data-processor-storage--analysis)
*   [Executor Lifecycle (States)](#executor-lifecycle-states)
*   [Logging & Persistence](#logging--persistence)
*   [Safe Execution Rules](#safe-execution-rules)

## 📋 Prerequisites

Install the required dependencies:

```bash
pip install pybit python-dotenv numpy scipy pandas
```

Your `.env` file must contain:

```dotenv
API_KEY=your_api_key
API_SECRET=your_api_secret
API_ENDPOINT=demo # or mainnet
```

## 🚀 Core Components

### 1. The Client (Execution)

The `Client` class handles all direct communication with Bybit, including automatic rounding of prices and quantities.

**Initialization:**

```python
from rexlapis import Client
client = Client(symbol="BTCUSDT", api_key="...", api_secret="...", api_endpoint="demo")
client.setup_bot(leverage=10)
```

**Key Methods:**

*   `get_current_price()`: Fetches the latest market price.
*   `get_usdt_balance()`: Returns available USDT in the Unified account.
*   `get_open_position()`: Returns details of the current active position.
*   `get_historical_klines(interval, start_time_ms)`: Fetches candles with auto-pagination and returns a Pandas DataFrame.
*   `place_limit_order(side, qty, price, post_only=True)`: Places a limit order with automatic precision rounding.

### 2. Trade Manager (Orchestration)

The `TradeManager` manages multiple `PositionExecutor` objects. It allows you to create complex grid or distribution-based trading strategies easily.

**Bulk Trade Creation:**

*   `create_linear_traders(...)`: Creates trades at equally spaced price intervals.
*   `create_normal_traders(...)`: Distributes trades based on a Gaussian (Normal) distribution (useful for mean-reversion).

**Execution Loop:**

```python
import time
from rexlapis import Client, TradeManager

# Assuming 'client' is already initialized as shown above
client = Client(symbol="BTCUSDT", api_key="YOUR_API_KEY", api_secret="YOUR_API_SECRET", api_endpoint="demo")
client.setup_bot(leverage=10)

manager = TradeManager(client, maker_offset_buy=0.5, maker_offset_sell=0.5)

# Example: Create 10 trades between 60k and 65k
manager.create_linear_traders(min_p=60000, max_p=65000, count=10, qty=0.01, profit=1.5)

# Main Loop (Heartbeat)
while True:
    manager.process_tick()
    time.sleep(5)
```

### 3. Data Processor (Storage & Analysis)

Handles saving market data to disk and resampling timeframes.

**Features:**

*   `save_to_csv(df)`: Saves candles to a local CSV file with automatic deduplication (based on timestamp).
*   `resample_candles(df, interval)`: Converts raw data (e.g., 1min) into custom timeframes (e.g., "5min", "1h").
*   `load_local_data()`: Loads the CSV into a DataFrame for visualization.

## 🔄 Executor Lifecycle (States)

Every trade managed by the `TradeManager` follows a strict state machine defined in `ExecutorState`:

*   `PENDING_ENTRY`: The trade is waiting to place its initial Buy order.
*   `PLACED_ENTRY`: The Buy order is active on the exchange.
*   `FILLED_WAIT`: The Buy order was filled; the bot is now "In Position".
*   `PLACED_EXIT`: The Sell (Reduce-Only) order is active on the exchange.
*   `COMPLETED`: The trade is closed. If `loop_trade` is `True`, it returns to `PENDING_ENTRY`.

## 📝 Logging & Persistence

### 1. Logs

The library creates a `./results` directory with two distinct log files:

*   `ops.log`: Technical logs, API errors, and order placements.
*   `pnl.log`: Clean record of closed trades and realized profit/loss.

### 2. State Recovery

To prevent data loss during a crash or restart, use the built-in save/load system:

```python
# Before shutting down
manager.save_to_disk("session_state.json")

# Upon restarting
manager.load_from_disk("session_state.json")
```

## 🛠️ Safe Execution Rules

*   **Post-Only Enforced**: By default, the `PositionExecutor` uses PostOnly for all orders to ensure you only pay Maker fees and never hit market orders by accident.
*   **Auto-Rounding**:
    *   Buy Orders: Always rounded **Down** (Floor) to ensure the price isn't higher than intended.
    *   Sell Orders: Always rounded **Up** (Ceiling).
    *   Quantity: Always rounded **Down** to avoid "Insufficient Margin" errors.