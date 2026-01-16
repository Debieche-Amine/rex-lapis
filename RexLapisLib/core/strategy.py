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
        """
        Lifecycle Method: Called on every new candle.
        
        :param df: A DataFrame containing historical data UP TO the current moment.
                   The last row is the 'current' candle.
        """
        pass

    # ==========================================================
    # Helper Methods (Proxies to Context)
    # ==========================================================
    def buy(self, qty: float, **kwargs):
        """Execute a Buy order."""
        return self.ctx.buy(qty, **kwargs)

    def sell(self, qty: float, **kwargs):
        """Execute a Sell order."""
        return self.ctx.sell(qty, **kwargs)
    
    @property
    def position(self):
        """Current open position."""
        return self.ctx.get_position()
        
    @property
    def balance(self):
        """Current wallet balance."""
        return self.ctx.get_balance()