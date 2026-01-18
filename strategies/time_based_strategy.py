import pandas as pd
from RexLapisLib import Strategy

class TimeBasedStrategy(Strategy):
    """
    Time Based Strategy: Buys IMMEDIATELY on start, then rotates every 5 candles.
    """
    
    def on_init(self):
        self.risk_per_trade = 0.50 
        self.trigger_candles = 5   
        
        self.candle_counter = self.trigger_candles 
        
        self.last_processed_time = None 
        
        if hasattr(self.ctx, 'client'):
            self.is_spot = (self.ctx.client.category == "spot")
            mode_name = "SPOT" if self.is_spot else "LINEAR"
        else:
            self.is_spot = False 
            mode_name = "BACKTEST"

        if self.is_spot:
            self.target_leverage = 1  
            print(f"Strategy Configured for {mode_name} (1x Leverage).")
        else:
            self.target_leverage = 10 
            if hasattr(self.ctx, 'set_leverage'):
                self.ctx.set_leverage(self.target_leverage)
            print(f"Strategy Configured for {mode_name} ({self.target_leverage}x Leverage).")

        print(f"Strategy Started. First trade will be IMMEDIATE.")
        
        current_balance = self.balance
        print(f"💰 Wallet Balance: {current_balance} USDT")

    def on_candle_tick(self, df: pd.DataFrame):
        current_candle_time = df.iloc[-1]['timestamp']
        
        # --- Time Filter ---
        if self.last_processed_time == current_candle_time:
            return 

        self.last_processed_time = current_candle_time
        
        if self.candle_counter < self.trigger_candles:
            self.candle_counter += 1
        
        print(f"⏳ Candle Counter: {self.candle_counter}/{self.trigger_candles}")

        if self.candle_counter < self.trigger_candles:
            return

        # --- EXECUTION ---
        current_candle = df.iloc[-1]
        price = current_candle['close']
        
        if not self.position:
            # --- BUY LOGIC ---
            wallet_balance = self.balance 
            margin_to_use = wallet_balance * self.risk_per_trade * self.target_leverage

            if self.is_spot:
                # SPOT: Buy in USDT
                qty = margin_to_use 
                qty = round(qty, 4)
                print(f"🚀 IMMEDIATE TRIGGER (SPOT): Buying {qty} USDT")
            else:
                # FUTURES: Buy in Coins
                qty = margin_to_use / price
                qty = round(qty, 3)
                print(f"🚀 IMMEDIATE TRIGGER (FUT): Buying {qty} XAUT")

            if qty > 0: 
                self.buy(qty=qty)
                # تصفير العداد لتبدأ دورة الانتظار الطبيعية (5 شموع)
                self.candle_counter = 0 
            else:
                print("❌ Quantity is 0 (Check Balance)")

        else:
            # --- SELL LOGIC ---
            print(f"📉 IMMEDIATE TRIGGER: SELLING Position")
            qty = self.position['qty']
            self.sell(qty=qty)
            # تصفير العداد
            self.candle_counter = 0