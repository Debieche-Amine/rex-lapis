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
        self.strategy.setup(self.context) 
        self.tech_engine = TechnicalEngine()

    def run(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes the backtest simulation.
        
        Mechanism:
        1. Pre-calculates indicators for speed (Vectorized).
        2. Iterates row-by-row passing sliced data to the strategy (No-Cheat).
        3. Updates context with the full candle to validate Limit/Post-Only orders.
        """
        start_time = time.time()
        print("Initializing Backtest...")
        
        if df.empty:
            return {"error": "DataFrame is empty"}

        # 1. Pre-calculate Indicators
        full_data = self.tech_engine.apply_all_indicators(df.copy())
        
        # 2. The Time Loop
        # Warmup period allows indicators (like RSI or MA) to stabilize
        warmup_period = 50 
        total_candles = len(full_data)

        for i in range(warmup_period, total_candles):
            # Slicing: Ensure the strategy only sees data up to the current index (No Look-ahead bias)
            current_slice = full_data.iloc[:i+1]
            current_candle = current_slice.iloc[-1]
            
            # --- CRITICAL: State Synchronization ---
            # Update Context State with full candle data (High, Low, Close, Timestamp)
            # This is required for the Context to check if Limit orders were hit.
            self.context.update_state(
                price=current_candle['close'], 
                time=current_candle['timestamp'],
                candle=current_candle  
            )
            
            # Execute Strategy logic
            self.strategy.on_candle_tick(current_slice)

        # 3. Finalize Results
        execution_time = time.time() - start_time
        print(f"Backtest completed in {execution_time:.2f}s")

        return self._generate_report(full_data)

    def _generate_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Formats the final simulation results for the Visualizer and Dashboard.
        Preserves all required metrics and trade history.
        """
        # Calculate ROI based on the starting balance and current context balance
        # Note: 10000 is the default; this should match the initial_balance from __init__
        initial = 10000 
        final = self.context.get_balance()
        roi = ((final - initial) / initial) * 100.0
        
        return {
            "initial_balance": initial,
            "final_balance": final,
            "roi": roi,
            "total_trades": len(self.context.trades),
            "trades_log": self.context.trades,
            "data_with_indicators": df 
        }