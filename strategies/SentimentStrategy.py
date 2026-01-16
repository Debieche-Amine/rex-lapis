import pandas as pd
from RexLapisLib import Strategy

class SentimentConfluenceStrategy(Strategy):
    """
    Advanced Confluence Strategy based on the RexLapis Terminal logic.
    It calculates a market sentiment score from -7 to +7 using multiple indicators.
    """

    def on_init(self):
        # 1. Strategy Parameters
        # These can be passed via self.parameters if needed
        self.buy_threshold = self.parameters.get('buy_threshold', 4)   # Strong Buy Signal
        self.sell_threshold = self.parameters.get('sell_threshold', -4) # Strong Sell Signal
        self.target_leverage = self.parameters.get('leverage', 5)
        self.risk_per_trade = self.parameters.get('risk', 0.5)         # Use 50% of balance
        
        # 2. Setup Context Leverage
        if hasattr(self.ctx, 'set_leverage'):
            self.ctx.set_leverage(self.target_leverage)
            
        print(f"--- Sentiment Strategy Initialized ---")
        print(f"Thresholds: Buy >= {self.buy_threshold} | Sell <= {self.sell_threshold}")
        print(f"Risk: {self.risk_per_trade*100}% at {self.target_leverage}x Leverage")

    def on_candle_tick(self, df: pd.DataFrame):
        """
        Main execution loop called for every candle by the BacktestEngine.
        Indicators are assumed to be pre-calculated by TechnicalEngine.
        """
        if len(df) < 2:
            return

        # Get the latest row
        row = df.iloc[-1]
        
        # --- ALGORITHMIC SCORING ENGINE ---
        # Extracted from the Terminal 'analyze_market_sentiment' logic
        score = 0
        
        # 1. SuperTrend Influence (Weight: 3)
        if row['trend_direction']: 
            score += 3
        else: 
            score -= 3
        
        # 2. RSI Mean Reversion (Weight: 2)
        if row['rsi'] < 30: 
            score += 2
        elif row['rsi'] > 70: 
            score -= 2
        
        # 3. MACD Momentum (Weight: 1)
        if row['macd'] > row['macd_signal']: 
            score += 1
        else: 
            score -= 1
        
        # 4. Price vs Bollinger Mid (Weight: 1)
        if row['close'] > row['bb_mid']: 
            score += 1
        else: 
            score -= 1

        # --- EXECUTION LOGIC ---
        current_price = row['close']
        pos = self.position #

        # A. BUY Logic (Enter Long)
        if score >= self.buy_threshold and not pos:
            # Calculate Quantity based on Risk and Buying Power
            buying_power = (self.balance * self.risk_per_trade) * self.target_leverage
            qty = buying_power / current_price
            
            if qty > 0:
                self.buy(qty=qty) #
                # print(f"SENTIMENT BUY | Score: {score} | Price: {current_price}")

        # B. SELL Logic (Exit Long / Trend Reversal)
        elif score <= self.sell_threshold and pos:
            if pos['side'] == 'Buy':
                self.sell(qty=pos['qty']) #
                # print(f"SENTIMENT EXIT | Score: {score} | Price: {current_price}")

    def on_finish(self):
        """Lifecycle method called after the backtest ends."""
        print("Simulation Finished. Processing results...")