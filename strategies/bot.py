import pandas as pd
from RexLapisLib import Strategy, TradeManager

class GridTradingStrategy(Strategy):
    """
    Equivalent version of your Grid Bot, structured for the Backtest Engine.
    """

    def on_init(self):
        # 1. Setup Environment (Equivalent to client setup)
        if hasattr(self.ctx, 'set_leverage'):
            self.ctx.set_leverage(5)
        
        # 2. Initialize Manager using the Simulation Context as a client
        self.manager = TradeManager(
            client=self.ctx, 
            maker_offset_buy=0.0001, 
            maker_offset_sell=0.0003
        )

        # 3. Create the Grid (Equivalent to your grid creation)
        self.manager.create_linear_traders(
            min_p=0.7194, 
            max_p=0.7284, 
            count=22, 
            qty=8, 
            profit=0.10, 
            loop_trade=True
        )

    def on_candle_tick(self, df: pd.DataFrame):
        # This replaces the 'while True' loop and processes the grid logic
        self.manager.process_tick()

    def on_finish(self):
        # Equivalent to your save_to_disk at the end of execution
        self.manager.save_to_disk("./results/linear_backtest.json")