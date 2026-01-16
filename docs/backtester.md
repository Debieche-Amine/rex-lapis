# Backtest Engine Documentation

The `BacktestEngine` is the orchestration layer designed to simulate trading strategies against historical market data. It focuses on high-fidelity simulation by enforcing a "No-Cheat" row-by-row execution loop, ensuring that your strategy can only make decisions based on data available at that specific point in time.

## How It Works

The engine follows a three-step execution process:

1.  **Vectorized Pre-calculation**: It uses the `TechnicalEngine` to calculate all indicators (RSI, MACD, etc.) for the entire dataset at once using optimized NumPy/Pandas operations for maximum speed.
2.  **The Time Loop**: It iterates through the data row-by-row. At each step, it slices the data to provide the `Strategy` only with the current and past candles.
3.  **Context Synchronization**: For every "tick" (candle), it updates the `BacktestContext` with the current price and timestamp to ensure accurate trade execution.

## Class API

### `__init__(self, strategy, initial_balance=10000)`

Initializes the engine with a specific strategy instance and starting capital.

*   **`strategy`**: An instance of a class inheriting from `Strategy`.
*   **`initial_balance`**: The starting USDT balance for the simulation.

### `run(self, df)`

Starts the simulation loop.

*   **`df`**: A pandas DataFrame containing historical OHLCV data.
*   **Warmup Period**: The engine automatically skips the first 50 candles to allow technical indicators (like Moving Averages) to have sufficient data to yield valid values.

**Returns**: A dictionary containing the final balance, ROI, total trades, trade log, and the processed DataFrame.

## Understanding the Results

The engine returns a comprehensive report dictionary:

| Key               | Description                                                                             |
| :---------------- | :-------------------------------------------------------------------------------------- |
| `initial_balance` | Starting wallet balance.                                                                |
| `final_balance`   | Wallet balance after the last candle and closing open positions.                        |
| `roi`             | Percentage Return on Investment.                                                        |
| `total_trades`    | Count of all Buy and Sell actions executed.                                             |
| `trades_log`      | A list of dictionaries containing price, type, and timestamp for every trade.           |
| `data_with_indicators` | The full DataFrame including all technical indicator columns.                         |

## Usage Example

```python
from RexLapisLib import BacktestEngine, DataProcessor
from my_strategies import RSICrossing

# 1. Load your data
dp = DataProcessor("BTCUSDT", "./data")
df = dp.load_local_data()

# 2. Setup the Strategy and Engine
strategy = RSICrossing()
engine = BacktestEngine(strategy, initial_balance=5000)

# 3. Run simulation
results = engine.run(df)

print(f"Final ROI: {results['roi']:.2f}%")
```

## Important Considerations

*   **Look-ahead Bias**: By using `full_data.iloc[:i+1]`, the engine ensures the strategy cannot "see" future candles, providing a realistic simulation of live market conditions.
*   **Execution Prices**: In the current backtest context, orders are executed at the close price of the current candle.