import pandas as pd
import os
import time

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
    

    def get_last_timestamp(self) -> int:
        """Returns the last timestamp in the CSV in milliseconds."""
        if not os.path.exists(self.storage_path):
            return 0
        df = pd.read_csv(self.storage_path)
        if df.empty:
            return 0
        return int(pd.to_datetime(df['timestamp']).max().timestamp() * 1000)

    def sync_gap(self, client):
        """Fetches missing data between CSV last date and NOW."""
        import time
        
        last_ts = self.get_last_timestamp()
        now_ts = int(time.time() * 1000)
        
        # If gap is more than 5 minutes (buffer)
        if last_ts == 0:
            print("No local data. Fetching recent history...")
            # Fetch last 5 days by default if file is empty
            start_ts = now_ts - (5 * 24 * 60 * 60 * 1000)
            new_data = client.get_historical_klines("1", start_ts)
            self.save_to_csv(new_data)
            
        elif (now_ts - last_ts) > 300000: # 5 minutes gap
            print(f"Syncing gap from {last_ts} to {now_ts}...")
            # Fetch missing candles
            new_data = client.get_historical_klines("1", last_ts)
            if not new_data.empty:
                self.save_to_csv(new_data)
                print(f"Downloaded {len(new_data)} new candles.")
            else:
                print("No new data available.")