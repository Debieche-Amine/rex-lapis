import pandas as pd
import time
from typing import Dict, Any
from .strategy import Strategy
from .context import BacktestContext
from .engine import TechnicalEngine 

class BacktestEngine:
    def __init__(self, strategy: Strategy, initial_balance: float = 10000):
        self.strategy = strategy
        self.context = BacktestContext(initial_balance)
        self.strategy.setup(self.context) # Inject dependencies
        self.tech_engine = TechnicalEngine()

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes the backtest simulation.
        
        Mechanism:
        1. Pre-calculates indicators for speed (Vectorized).
        2. Iterates row-by-row passing sliced data to the strategy (No-Cheat).
        """
        start_time = time.time()
        print("Initializing Backtest...")
        
        if df.empty:
            return {"error": "DataFrame is empty"}

        # 1. Pre-calculate Indicators
        # We assume TechnicalEngine.apply_all_indicators returns the DF with new columns
        full_data = self.tech_engine.apply_all_indicators(df.copy())
        
        # 2. The Time Loop
        # We start from index 50 to allow indicators (like MA_50) to have valid values
        warmup_period = 50 
        total_candles = len(full_data)
        
        if total_candles < warmup_period:
             return {"error": "Not enough data for warmup period"}

        for i in range(warmup_period, total_candles):
            # Slicing: Get data from start [0] up to current index [i] (inclusive)
            # This ensures the strategy cannot see i+1 (The Future)
            current_slice = full_data.iloc[:i+1]
            
            # Update Context State (Current Price and Time)
            current_candle = current_slice.iloc[-1]
            self.context.update_state(
                price=current_candle['close'], 
                time=current_candle['timestamp']
            )
            
            # Execute Strategy Logic
            self.strategy.on_candle_tick(current_slice)

        # 3. Compile Results
        execution_time = time.time() - start_time
        print(f"Backtest completed in {execution_time:.2f}s")

        return self._generate_report(full_data)

    def _generate_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Formats the results for the Dashboard."""
        
        # Calculate ROI
        initial = 10000 # hardcoded base for now, should match context init
        final = self.context.balance
        roi = ((final - initial) / initial) * 100.0
        
        return {
            "initial_balance": initial,
            "final_balance": final,
            "roi": roi,
            "total_trades": len(self.context.trades),
            "trades_log": self.context.trades,
            "data_with_indicators": df 
        }