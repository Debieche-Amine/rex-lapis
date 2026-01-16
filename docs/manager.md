
# Trade Manager & Position Executor Documentation

The `TradeManager` and `PositionExecutor` components form the execution and management layer of RexLapis Lab. While the `Strategy` class handles logic, these classes manage the technical lifecycle of orders, ensuring that trades are executed as "Maker" orders to minimize fees and providing tools for bulk algorithmic trade distribution.

## 🔄 PositionExecutor: The Trade Lifecycle

The `PositionExecutor` manages a single trade through a robust state machine. This ensures that the system knows exactly what to do if an order is partially filled, cancelled, or rejected.

### Execution States

*   **PENDING_ENTRY**: The initial state where the buy order is prepared.
*   **PLACED_ENTRY**: The buy order is active on the exchange.
*   **FILLED_WAIT**: The buy order is filled; the executor is now waiting for the target exit price to be reached.
*   **PLACED_EXIT**: The sell order is active on the exchange.
*   **COMPLETED**: The trade cycle is finished, and PnL is logged.

### Key Features

*   **Maker Protection**: Uses `post_only=True` to ensure you always receive Maker rebates rather than paying Taker fees.
*   **Maker Offsets**: Automatically adjusts limit prices using `maker_offset` to stay ahead of the order book.
*   **Loop Trading**: If `loop_trade` is enabled, the executor automatically resets to `PENDING_ENTRY` after a successful exit.

## 🏛️ TradeManager: The Orchestrator

The `TradeManager` acts as the "brain" for multiple executors. It handles synchronization with the exchange and provides algorithms to generate complex trade grids.

### 1. Bulk Generation Algorithms

The manager allows you to deploy dozens of trades instantly using mathematical distributions:

*   **Linear Distribution**: Generates trades at equally spaced price intervals between a minimum and maximum price.
*   **Normal (Gaussian) Distribution**: Concentrates more trades around a specific mean (average price) and fewer at the extremes, ideal for market-making around a fair value.

### 2. The Heartbeat (process\_tick)

This method is called periodically (e.g., every 2–5 seconds) to:

*   Fetch the current market price.
*   Synchronize open orders and trade history from the exchange.
*   Iterate through all active `PositionExecutor`s to trigger their next state transition.
*   Clean up completed trades to free up memory.

## 🛠️ Usage Example

### Creating a Gaussian Trade Grid

```python
from RexLapisLib import TradeManager, Client
import time

# Initialize Client and Manager
client = Client(...)
manager = TradeManager(client, maker_offset_buy=0.1, maker_offset_sell=0.1)

# Generate 20 trades between $60,000 and $65,000
# Mean is automatically set to the center, or you can specify 'mean'
manager.create_normal_traders(
    min_p=60000,
    max_p=65000,
    count=20,
    qty=0.001,
    profit=0.5,  # 0.5% profit target per trade
    loop=True    # Continuous trading
)

# Run the heartbeat loop
while True:
    manager.process_tick()
    time.sleep(2)
```

## 📊 Logging and Persistence

*   **Financial Tracking**: Every closed trade is logged in `./results/pnl.log` with the exact entry/exit prices and realized PnL.
*   **Operations Tracking**: Technical errors (like API timeouts) are logged in `./results/ops.log`.
*   **Persistence**: Use `save_to_disk()` and `load_from_disk()` to save the state of your traders to a JSON file, allowing you to resume trading after a bot restart without losing track of open positions.