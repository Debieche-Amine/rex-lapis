# RexLapis Lab 🧪

A High-Performance Algorithmic Trading Framework for Bybit.

RexLapis Lab is a comprehensive Python-based trading library designed to bridge the gap between historical backtesting and live execution. It provides a unified interface where a single strategy can be simulated against years of data or deployed to live markets with minimal code changes.

## 🚀 Key Features

*   **Unified Context System:** Switch between `BacktestContext` and `LiveContext` seamlessly using the `IContext` interface.
*   **Precision Execution:** Automatic handling of price ticks, quantity steps, and rounding specifically for Bybit V5.
*   **Advanced TA Engine:** Built-in support for RSI, MACD, Bollinger Bands, and a custom SuperTrend with sentiment scoring.
*   **Automated Trade Management:** lifecycle management of trades from `PENDING` to `COMPLETED` with "Post-Only" support to ensure Maker fees.
*   **Visual Analytics:** Interactive Streamlit dashboard to visualize trades, PnL, and technical indicators on Plotly charts.
*   **Smart Data Sync:** Local CSV storage management with automatic gap synchronization from the exchange.

## 📂 Project Structure & Navigation

You can find detailed documentation for each component in the `docs/` folder:

| Component          | Description                                                      | Documentation          |
| :----------------- | :--------------------------------------------------------------- | :--------------------- |
| **Core Client**    | Bybit V5 API integration and asset precision management.         | `docs/client.md`       |
| **Strategy Base**  | The foundation for building custom trading logic.                | `docs/strategy.md`     |
| **Backtest Engine**| Row-by-row "No-Cheat" simulation environment.                    | `docs/backtester.md`   |
| **Trade Manager**  | Bulk trade generation (Linear/Gaussian) and lifecycle tracking. | `docs/manager.md`      |
| **Technical Engine**| Vectorized indicator calculations and market sentiment scoring.  | `docs/engine.md`       |
| **Data Processor** | CSV management, resampling, and historical data syncing.         | `docs/data_processor.md` |

## 🛠️ Quick Start

1.  **Installation**

    Ensure you have the required dependencies:

    ```bash
    pip install pandas pandas_ta numpy scipy pybit streamlit plotly python-dotenv
    ```

2.  **Basic Backtest Example**

    ```python
    from RexLapisLib import BacktestEngine, Strategy, DataProcessor

    class MyStrategy(Strategy):
        def on_candle_tick(self, df):
            if df['rsi'].iloc[-1] < 30:
                self.buy(qty=0.01)
            elif df['rsi'].iloc[-1] > 70:
                self.sell(qty=0.01)

    # Initialize data and engine
    dp = DataProcessor("BTCUSDT", "./data")
    df = dp.load_local_data() 

    engine = BacktestEngine(MyStrategy())
    results = engine.run(df)
    ```

    *Note: The `BacktestEngine` uses a warmup period (default 50 candles) to ensure indicators have sufficient data for calculation.*

## 📊 Visualization

After running a simulation, you can launch the interactive dashboard:

```python
from RexLapisLib import show_dashboard

# This launches a Streamlit instance automatically
show_dashboard(results) 
```

The dashboard provides a performance summary including Final Balance, ROI, and a full Trade Log.