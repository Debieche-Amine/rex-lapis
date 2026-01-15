# Rex Lapis: The Geo Archon Trading Engine

"I am the Lord of Geo. My word is a contract, and my contract is unbreakable."

Rex Lapis is an integrated automated trading and technical analysis framework specifically designed for the Bybit V5 platform. The project combines the precision of mathematical contracts (predictions) with the power of programmatic execution, offering full support for Linear Futures and Spot (XAUTUSDT).

## 📈 0. Gold Prediction Model (The Geo Archon's Logic)

The engine bases its primary gold predictions on a precise Exponential Growth Model:

$$gold(t) = e^b \cdot e^{a \cdot t}$$

**Mathematical Parameters:**
*   **Slope ($a$):** `0.001012899940494811`
*   **Intercept ($b$):** `7.586419247136773`
*   **Time ($t$):** Number of days elapsed since `2024-01-01`

## 🛠️ 1. Installation & Setup

### Requirements

```bash
Bash
pip install pybit python-dotenv numpy scipy pandas streamlit plotly
```

### Environment Configuration

Create a `.env` file in the root directory:

```dotenv
API_KEY=your_api_key
API_SECRET=your_api_secret
API_ENDPOINT=demo  # Options: demo or mainnet
```

**Note:** For real XAUT data, using `mainnet` is recommended.

## 🚀 2. Usage Examples

### Fetching Gold Data (XAUUSD/XAUT)

The library supports fetching historical data and saving it in CSV format with deduplication.

```python
# Example for fetching Spot Gold data
from RexLapisLib import Client, DataProcessor

client = Client(symbol="XAUTUSDT", category="spot", api_endpoint="mainnet")
processor = DataProcessor(symbol="XAUTUSDT", storage_dir="./data")

# Fetch data for the last 48 hours with 1-minute interval
start_ts = ... # timestamp in milliseconds
historical_df = client.get_historical_klines(interval="1", start_time_ms=start_ts)
processor.save_to_csv(historical_df)
```

## 🖥️ 3. RexLapis Pro Terminal (Visualizer)

The project includes an advanced analytical interface using Streamlit and Plotly.

### Running the Interface:

```bash
python -m streamlit run examples\visualize.py 
```

### Terminal Features:

*   **SuperTrend Algorithm:** An intelligent trend detector based on ATR.
*   **Market Intelligence Score:** An evaluation system (from -7 to +7) that combines RSI, MACD, and Bollinger Bands to provide entry/exit signals.
*   **Confluence Engine:** Does not rely on a single indicator but on the "confluence" of multiple indicators to ensure contract accuracy.
*   **No-Cheat Principle:** All calculations are based solely on the current time $t$ and preceding data, ensuring realistic results.

## 🛡️ 4. Rules of the Contract

*   **Maker Enforcement:** The engine consistently uses `PostOnly` orders to ensure the capture of Maker Fees.
*   **Safety First:** The account is automatically switched to Isolated Margin upon startup.
*   **Data Integrity:** Data is stored locally to prevent excessive API consumption and allow for rapid analysis.

---
