import pandas as pd
from typing import Optional, Dict, Any
from .context import IContext

class Strategy:
    """
    Base Strategy Class. 
    Users should inherit from this class and implement 'on_candle_tick'.
    """
    def __init__(self):
        self.ctx: Optional[IContext] = None 
        self.parameters: Dict[str, Any] = {}

    def setup(self, ctx: IContext, **kwargs):
        """Internal method to link the Strategy with the Context (Live or Backtest)."""
        self.ctx = ctx
        self.parameters = kwargs
        self.on_init()

    def on_init(self):
        """
        Lifecycle Method: Called once when the strategy starts.
        Use this to define variables or indicators if needed.
        """
        pass

    def on_candle_tick(self, df: pd.DataFrame):
        current_price = df.iloc[-1]['close']
        
        if not self.position:
            target_price = current_price * 0.999 
            
            self.buy(
                qty=10, 
                price=target_price, 
                post_only=True 
            )
            
        else:
            self.sell(
                qty=self.position['qty'], 
                reduce_only=True 
            )

    # ==========================================================
    # Helper Methods (Proxies to Context)
    # ==========================================================
    def buy(self, qty: float, price: float = None, post_only: bool = False, reduce_only: bool = False, **kwargs):
        """Execute a Buy order with professional flags."""
        return self.ctx.buy(qty, price=price, post_only=post_only, reduce_only=reduce_only, **kwargs)

    def sell(self, qty: float, price: float = None, post_only: bool = False, reduce_only: bool = False, **kwargs):
        """Execute a Sell order with professional flags."""
        return self.ctx.sell(qty, price=price, post_only=post_only, reduce_only=reduce_only, **kwargs)
    
    @property
    def position(self):
        """Current open position."""
        return self.ctx.get_position()
        
    @property
    def balance(self):
        """Current wallet balance."""
        return self.ctx.get_balance()