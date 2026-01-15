import pandas as pd
import os

class DataProcessor:
    def __init__(self, symbol: str, storage_dir: str):
        """Initializes storage path and ensures directory exists."""
        self.symbol = symbol.upper()
        os.makedirs(storage_dir, exist_ok=True)
        self.storage_path = os.path.join(storage_dir, f"{self.symbol}_history.csv")

    def save_to_csv(self, df: pd.DataFrame):
        """Saves data to CSV with deduplication."""
        if os.path.exists(self.storage_path):
            existing_df = pd.read_csv(self.storage_path)
            existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
            df = pd.concat([existing_df, df]).drop_duplicates(subset=['timestamp'])
        
        df.sort_values("timestamp", inplace=True)
        df.to_csv(self.storage_path, index=False)
        print(f"File Synchronized: {self.storage_path}")

    def load_local_data(self) -> pd.DataFrame:
        """Loads stored CSV data into a DataFrame. CRITICAL FOR VISUALIZER."""
        if os.path.exists(self.storage_path):
            df = pd.read_csv(self.storage_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        return pd.DataFrame()

    def resample_candles(self, df: pd.DataFrame, custom_interval: str):
        """Custom resampling with modern Pandas aliases to avoid FutureWarnings."""
        custom_interval = custom_interval.replace('T', 'min').replace('H', 'h')
        
        df = df.set_index("timestamp")
        resampled = df.resample(custom_interval).agg({
            "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
        }).dropna()
        return resampled.reset_index()