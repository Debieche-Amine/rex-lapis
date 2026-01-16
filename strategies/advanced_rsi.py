import pandas as pd
from RexLapisLib.core.strategy import Strategy

class AdvancedRSIStrategy(Strategy):
    """
    Advanced Strategy with Leverage & Portfolio Management.
    """
    
    def on_init(self):
        # 1. Configuration
        self.rsi_period = 14
        self.target_leverage = 10     # 10x Leverage
        self.risk_per_trade = 0.50    # Use 50% of available wallet balance
        
        # 2. Set Leverage in the Engine/Exchange
        # This works for both Backtest (Context) and Live (Bybit Client)
        if hasattr(self.ctx, 'set_leverage'):
            self.ctx.set_leverage(self.target_leverage)
            
        print(f"Strategy Started. Lev: {self.target_leverage}x | Risk: {self.risk_per_trade*100}%")

    def on_candle_tick(self, df: pd.DataFrame):
        current_candle = df.iloc[-1]
        if 'rsi' not in current_candle: return

        rsi = current_candle['rsi']
        price = current_candle['close']
        
        # --- BUY LOGIC ---
        if rsi < 30 and not self.position:
            # Portfolio Management Logic
            
            # 1. Get Wallet Balance
            wallet_balance = self.balance 
            
            # 2. Determine Allocation (Risk % * Balance)
            # Example: $10,000 * 0.50 = $5,000 to use for margin
            margin_to_use = wallet_balance * self.risk_per_trade
            
            # 3. Calculate Buying Power (Margin * Leverage)
            # $5,000 * 10 = $50,000 Total Order Value
            buying_power = margin_to_use * self.target_leverage
            
            # 4. Calculate Quantity
            qty = buying_power / price
            qty = round(qty, 3)

            # Execution
            if qty > 0.001: # Min order check
                # print(f"BUY | Bal: {wallet_balance} | Margin: {margin_to_use} | Pow: {buying_power} | Qty: {qty}")
                self.buy(qty=qty)

        # --- SELL LOGIC ---
        elif rsi > 70 and self.position:
            qty = self.position['qty']
            self.sell(qty=qty)