
# Strategy Base Class Documentation

The `Strategy` class is the core component for defining your trading logic. It's an abstract base class that ensures a unified interface for both backtesting and live trading environments.

## Creating a Custom Strategy

To create your own strategy, inherit from the `Strategy` class and implement the `on_candle_tick` method.

```python
from RexLapisLib import Strategy

class MyMovingAverageStrategy(Strategy):
    def on_init(self):
        # Called once at the start of the strategy.
        print("Strategy Started!")

    def on_candle_tick(self, df):
        # This is the main logic loop for your strategy.
        pass
```

## Lifecycle Methods

### `on_init(self)`

This method is executed only once when the strategy begins. It's ideal for initializing variables, setting up indicators, or defining initial parameters.

### `on_candle_tick(self, df)`

This is the central method of your strategy, invoked for every new candle processed (in backtesting) or received (in live trading).

*   **`df`** (pd.DataFrame): A DataFrame containing historical market data up to the current moment. The last row of this DataFrame represents the "current" candle.

## Trading Helpers (Proxies)

The `Strategy` class provides convenient proxy methods to interact with the underlying `Context`.

### Execution

*   `self.buy(qty, **kwargs)`: Executes a buy order.
*   `self.sell(qty, **kwargs)`: Executes a sell order.

### State Access

*   `self.position`: A property that returns the current open position object or `None` if no position is open.
*   `self.balance`: A property that returns the current available wallet balance.

## Internal Mechanics

### `setup(ctx, **kwargs)`

This internal method connects the strategy to the execution environment (`LiveContext` or `BacktestContext`) and stores any custom parameters passed during engine initialization. You typically do not need to call this method manually, as the `BacktestEngine` handles it.

## Complete Example: RSI Mean Reversion Strategy

```python
from RexLapisLib import Strategy

class RSIReversion(Strategy):
    def on_init(self):
        # Retrieve custom parameters or set defaults
        self.rsi_period = self.parameters.get('rsi_period', 14)
        self.buy_threshold = 30
        self.sell_threshold = 70

    def on_candle_tick(self, df):
        # Indicators are pre-calculated by the engine for efficiency
        current_rsi = df['rsi'].iloc[-1]
        
        # Get current position status
        pos = self.position
        
        if not pos:  # If no position is open
            if current_rsi < self.buy_threshold:
                self.buy(qty=0.01)  # Enter a buy position
        else:  # If a position is already open
            if pos['side'] == 'Buy' and current_rsi > self.sell_threshold:
                self.sell(qty=0.01)  # Close the buy position
```