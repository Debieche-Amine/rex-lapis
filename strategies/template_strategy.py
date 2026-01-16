import pandas as pd
import pandas_ta as ta
from RexLapisLib.core.strategy import Strategy

class MyNewStrategy(Strategy):
    """
    Template Strategy.
    Developer: [Name]
    Description: [Brief description]
    """

    def on_init(self):
        """
        Called once at the beginning.
        Set up indicators, leverage, and risk management here.
        """
        # 1. Leverage Setup (e.g., 5x)
        self.leverage = 5
        if hasattr(self.ctx, 'set_leverage'):
            self.ctx.set_leverage(self.leverage)
            
        # 2. Parameters
        self.rsi_len = 14
        self.ma_len = 50
        print(f"Strategy Initialized with {self.leverage}x Leverage")

    def on_candle_tick(self, df: pd.DataFrame):
        """
        Called on every new candle close.
        df contains historical data up to the current moment.
        """
        # 1. Data Prep (Get last candle)
        # Note: RexLapis Engine handles indicators, or you can calc here
        current = df.iloc[-1]
        close_price = current['close']
        
        # Example: Calculate Indicator on the fly if not in DF
        # rsi = ta.rsi(df['close'], length=self.rsi_len).iloc[-1]

        # 2. Logic
        # if rsi < 30 and not self.position:
        #     self.buy(qty=1.0)
        
        # if rsi > 70 and self.position:
        #     self.sell(qty=self.position['qty'])
        
        pass