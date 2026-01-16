import pandas as pd
from RexLapisLib import Strategy, TradeManager

class XAUTSpecial(Strategy):
    """
    Equivalent version of your XAUT Normal Grid with Auto Mean,
    structured to run inside the fixed run_simulation.py.
    """

    def on_init(self):
        # 1. Setting up Leverage in the simulation environment
        # Equivalent to client.setup_bot(leverage=5)
        if hasattr(self.ctx, 'set_leverage'):
            self.ctx.set_leverage(5)
            
        # 2. Initialize the Manager using the simulation context
        # maker_offset is set to 1 as per your script requirements
        self.manager = TradeManager(
            client=self.ctx, 
            maker_offset_buy=1.0, 
            maker_offset_sell=1.0
        )

        # 3. Create Normal (Gaussian) Traders with Auto-Mean calculation
        # Parameters: min_p=4401, max_p=4553, count=17, qty=0.002, profit=0.30
        # mean=None triggers the automatic calculation in manager.py: (min_p + max_p) / 2
        print(f"🏗️ Grid Strategy Initialized: Normal Distribution (Auto-Mean)")
        self.manager.create_normal_traders(
            min_p=4401.0, 
            max_p=4553.0, 
            count=17, 
            qty=0.002, 
            profit=0.30, 
            loop=True,
            mean=None,    # Auto-mean calculation
            sigma=4.0     # Equivalent to your sigma_factor
        )

    def on_candle_tick(self, df: pd.DataFrame):
        """
        Executed on every candle by the BacktestEngine.
        Replaces the manual 'while True' loop.
        """
        self.manager.process_tick()

    def on_finish(self):
        """
        Saves the final backtest state to disk after completion.
        """
        self.manager.save_to_disk("./results/xaut_auto_backtest.json")