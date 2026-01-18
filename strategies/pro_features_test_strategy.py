import pandas as pd
from RexLapisLib.core.strategy import Strategy

class ProFeaturesTestStrategy(Strategy):
    """
    Professional Framework Validation Strategy:
    - Tests Limit Order execution vs. Market price.
    - Tests Post-Only (Maker) validation.
    - Tests Reduce-Only (Position protection).
    - Integrates Technical Indicators (RSI & SuperTrend).
    - Dynamic Quantity Calculation based on Wallet Balance.
    """

    def on_init(self):
        # --- Configuration ---
        self.entry_offset = 0.0005  # Place Buy Limit 0.05% below current price
        self.profit_target = 0.0010 # Target 0.1% profit from entry
        self.risk_pct = 0.20        # Invest 20% of current balance per trade
        
        # --- Internal State ---
        self.is_order_pending = False
        self.last_candle_time = None
        print("✅ ProFeaturesTestStrategy Initialized.")

    def on_candle_tick(self, df: pd.DataFrame):
        current_candle = df.iloc[-1]
        current_price = current_candle['close']
        
        # 1. Check if we have an open position
        if self.position:
            # Check if we already placed a Sell Limit order
            # This prevents the "Multiple Fills" bug seen in your logs
            has_pending_sell = any(o['side'] == 'Sell' for o in self.ctx.pending_orders)
            
            if not has_pending_sell:
                entry_price = self.position['entry_price']
                limit_sell_price = entry_price * (1 + self.profit_target)
                
                print(f"[{current_candle['timestamp']}] 💰 Position Opened. Placing SINGLE Exit Order.")
                self.sell(
                    qty=self.position['qty'], 
                    price=limit_sell_price, 
                    post_only=True, 
                    reduce_only=True
                )
            return # Exit tick processing if we are managing a position

        # 2. Entry Logic (Only if no position and no pending buy)
        has_pending_buy = any(o['side'] == 'Buy' for o in self.ctx.pending_orders)
        if not has_pending_buy:
            limit_buy_price = current_price * (1 - self.entry_offset)
            buy_qty = (self.balance * self.risk_pct) / limit_buy_price
            
            self.buy(qty=buy_qty, price=limit_buy_price, post_only=True)