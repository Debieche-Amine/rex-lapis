import pandas as pd
import pandas_ta as ta
import numpy as np

class TechnicalEngine:
    """
    Independent Algorithmic Engine for technical indicators and market analysis.
    Separated from the UI to ensure logic can be used in live trading or backtesting.
    """

    @staticmethod
    def apply_indicators(df: pd.DataFrame, atr_period=10, atr_mult=3.0):
        # --- 1. RSI (Simple Mean Version) ---
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        # --- 2. MACD ---
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # --- 3. Bollinger Bands ---
        df['bb_mid'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)

        # --- 4. SuperTrend (No-Cheat Logic) ---
        hl2 = (df['high'] + df['low']) / 2
        df['tr'] = df[['high', 'low', 'close']].apply(lambda x: max(x[0]-x[1], abs(x[0]-x[2]), abs(x[1]-x[2])), axis=1) # Simplified TR
        df['atr'] = df['tr'].ewm(alpha=1/atr_period, adjust=False).mean()

        upper_basic = hl2 + (atr_mult * df['atr'])
        lower_basic = hl2 - (atr_mult * df['atr'])
        
        # Iterative Loop for SuperTrend
        ub = upper_basic.values
        lb = lower_basic.values
        close = df['close'].values
        upper_band = np.zeros(len(df))
        lower_band = np.zeros(len(df))
        supertrend = np.zeros(len(df), dtype=bool)

        for i in range(1, len(df)):
            upper_band[i] = ub[i] if ub[i] < upper_band[i-1] or close[i-1] > upper_band[i-1] else upper_band[i-1]
            lower_band[i] = lb[i] if lb[i] > lower_band[i-1] or close[i-1] < lower_band[i-1] else lower_band[i-1]
            
            if supertrend[i-1] and close[i] <= lower_band[i]: supertrend[i] = False
            elif not supertrend[i-1] and close[i] >= upper_band[i]: supertrend[i] = True
            else: supertrend[i] = supertrend[i-1]

        df['trend_direction'] = supertrend
        return df
    
    @staticmethod
    def calculate_confluence_score(row):
        score = 0
        if row['trend_direction']: score += 3  # SuperTrend
        else: score -= 3
        
        if row['rsi'] < 30: score += 2        # RSI Oversold
        elif row['rsi'] > 70: score -= 2      # RSI Overbought
        
        if row['macd'] > row['macd_signal']: score += 1 # MACD Momentum
        else: score -= 1
        
        if row['close'] > row['bb_mid']: score += 1     # Price vs BB Mid
        else: score -= 1
        return score

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14):
        """Calculate Relative Strength Index (RSI)"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast=12, slow=26, signal=9):
        """Calculate Moving Average Convergence Divergence (MACD)"""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        return df

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        df['bb_mid'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * std_dev)
        return df

    @staticmethod
    def calculate_supertrend(df: pd.DataFrame, period=10, multiplier=3):
        """
        Calculate SuperTrend with high precision.
        Uses (t-1) logic to prevent look-ahead bias.
        """
        hl2 = (df['high'] + df['low']) / 2
        
        # ATR Calculation
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        df['atr'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()

        upper_basic = hl2 + (multiplier * df['atr'])
        lower_basic = hl2 - (multiplier * df['atr'])

        close = df['close'].values
        ub = upper_basic.values
        lb = lower_basic.values
        
        upper_band = np.zeros(len(df))
        lower_band = np.zeros(len(df))
        supertrend = np.zeros(len(df), dtype=bool) 
        trend_line = np.zeros(len(df))

        for i in range(1, len(df)):
            # Final Upper Band Calculation
            if ub[i] < upper_band[i-1] or close[i-1] > upper_band[i-1]:
                upper_band[i] = ub[i]
            else:
                upper_band[i] = upper_band[i-1]

            # Final Lower Band Calculation
            if lb[i] > lower_band[i-1] or close[i-1] < lower_band[i-1]:
                lower_band[i] = lb[i]
            else:
                lower_band[i] = lower_band[i-1]

            # Trend Direction Logic
            if supertrend[i-1] == True and close[i] <= lower_band[i]:
                supertrend[i] = False
            elif supertrend[i-1] == False and close[i] >= upper_band[i]:
                supertrend[i] = True
            else:
                supertrend[i] = supertrend[i-1]
                
            # Set the visualization line
            trend_line[i] = lower_band[i] if supertrend[i] else upper_band[i]

        df['supertrend_line'] = trend_line
        df['trend_direction'] = supertrend
        return df

    @staticmethod
    def analyze_market_sentiment(row):
        """
        Sentiment Engine: Calculates a Confluence Score based on multiple indicators.
        Returns a score between -7 and +7.
        """
        score = 0
        # 1. SuperTrend Influence
        if row['trend_direction']: score += 3
        else: score -= 3
        
        # 2. RSI Mean Reversion
        if row['rsi'] < 30: score += 2
        elif row['rsi'] > 70: score -= 2
        
        # 3. MACD Momentum
        if row['macd'] > row['macd_signal']: score += 1
        else: score -= 1
        
        # 4. Price vs Bollinger Mid
        if row['close'] > row['bb_mid']: score += 1
        else: score -= 1
        return score

    def apply_all_indicators(self, df: pd.DataFrame, atr_period=10, atr_mult=3.0):
        """Wraps all technical calculations for a single DataFrame."""
        if df.empty: return df
        df = self.calculate_supertrend(df, period=atr_period, multiplier=atr_mult)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df = self.calculate_macd(df)
        df = self.calculate_bollinger_bands(df)
        df['score'] = df.apply(self.analyze_market_sentiment, axis=1)
        return df