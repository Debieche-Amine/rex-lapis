import pandas as pd
from RexLapisLib import Strategy, TradeManager

class XAUTR9S4(Strategy):
    """
    Equivalent version of your XAUT Normal Grid Bot, 
    structured for the Backtest Engine.
    """

    def on_init(self):
        # 1. Configuration (Leverage Setup)
        # Equivalent to client.setup_bot(leverage=5)
        if hasattr(self.ctx, 'set_leverage'):
            self.ctx.set_leverage(5)
            
        # 2. Initialize Manager using the Simulation Context
        # maker_offset is set to 1 as per your original script
        self.manager = TradeManager(
            client=self.ctx, 
            maker_offset_buy=1.0, 
            maker_offset_sell=1.0
        )

        # 3. Create Normal (Gaussian) Grid
        # Mapping your parameters to the Technical names in manager.py
        # min_p=4146, max_p=4553, count=73, qty=0.002, profit=0.30
        print(f"🏗️ Initializing Normal Distribution Grid for {self.ctx.__class__.__name__}")
        self.manager.create_normal_traders(
            min_p=4146.0, 
            max_p=4553.0, 
            count=73, 
            qty=0.002, 
            profit=0.30, 
            loop=True,
            mean=4360.0,  # Corresponds to your mean_price
            sigma=4.0     # Corresponds to your sigma_factor
        )

    def on_candle_tick(self, df: pd.DataFrame):
        """
        Processes the heartbeat for every candle in the backtest.
        Replaces the 'while True' loop and signal handling.
        """
        self.manager.process_tick()

    def on_finish(self):
        """
        Saves final state after the simulation ends.
        """
        self.manager.save_to_disk("./results/xaut_backtest_results.json")