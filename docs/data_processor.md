
# Data Processor Documentation

The `DataProcessor` class is the storage and synchronization hub of RexLapis Lab. It manages the lifecycle of market data by handling local CSV storage, deduplicating records, and automatically filling gaps between your local data and the live exchange.

## Core Responsibilities

*   **Persistent Storage**: Manages local CSV files for specific symbols to ensure data is available offline for backtesting.
*   **Data Integrity**: Implements deduplication logic during saves to prevent overlapping timestamps in your datasets.
*   **Gap Synchronization**: Automatically detects the time difference between your last saved candle and the current time to fetch missing data from the exchange.
*   **Timeframe Resampling**: Provides tools to convert high-frequency data (e.g., 1-minute) into custom intervals like 5-minute, 1-hour, or 1-day candles.

## Class API

### `__init__(self, symbol, storage_dir)`

Initializes the processor and ensures the storage directory exists on your disk.

*   `symbol`: The trading pair (e.g., "BTCUSDT").
*   `storage_dir`: The folder where CSV files will be saved.

### `save_to_csv(self, df)`

Appends new data to the local file.

*   It automatically merges the new DataFrame with existing data.
*   It drops duplicate rows based on the timestamp column and sorts the result chronologically.

### `load_local_data(self)`

Loads the stored CSV data into a Pandas DataFrame for use in the `BacktestEngine` or `TechnicalEngine`.

*   It automatically converts the timestamp column into proper datetime objects.

### `resample_candles(self, df, custom_interval)`

Transforms a DataFrame into a different timeframe.

*   It uses modern Pandas aliases (e.g., `min` instead of `T`) to ensure compatibility with future Python versions.
*   It aggregates Open, High, Low, Close, and Volume (OHLCV) correctly.

### `sync_gap(self, client)`

The primary tool for keeping your data up to date.

*   It checks the `last_timestamp` in your local file.
*   If no data exists, it fetches the last 5 days of history by default.
*   If a gap of more than 5 minutes is detected, it fetches only the missing candles from the exchange and saves them.

## Usage Example

```python
from RexLapisLib import DataProcessor, Client

# 1. Initialize Processor
dp = DataProcessor(symbol="BTCUSDT", storage_dir="./market_data")

# 2. Sync with Bybit (Live)
client = Client(symbol="BTCUSDT", api_key="...", api_secret="...")
dp.sync_gap(client)

# 3. Load data for Analysis
df_1min = dp.load_local_data()

# 4. Create 1-Hour Candles for Strategy
df_1h = dp.resample_candles(df_1min, custom_interval="1H")
```

## Technical Requirements

*   **Pandas**: The processor relies heavily on Pandas for resampling and deduplication.
*   **Directory Permissions**: Ensure the application has write access to the `storage_dir`.