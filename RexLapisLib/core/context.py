from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd

class IContext(ABC):
    """Unified Interface for Strategy Interaction."""
    
    @abstractmethod
    def set_leverage(self, leverage: int):
        """Sets the leverage for the account/symbol."""
        pass

    @abstractmethod
    def buy(self, qty: float, price: float = None, stop_loss: float = None, take_profit=None):
        pass

    @abstractmethod
    def sell(self, qty: float, price: float = None, stop_loss: float = None, take_profit=None):
        pass

    @abstractmethod
    def get_balance(self) -> float:
        pass

    @abstractmethod
    def get_position(self) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def log(self, message: str):
        pass

# ---------------------------------------------------------
# Live Context
# ---------------------------------------------------------
class LiveContext(IContext):
    def __init__(self, client):
        self.client = client
    
    def set_leverage(self, leverage: int):
        # Calls the Bybit Client to set leverage on the exchange
        self.client.setup_bot(leverage) 

    def buy(self, qty, price=None, stop_loss=None, take_profit=None):
        if price:
            return self.client.place_limit_order("Buy", qty, price)
        else:
            return self.client.place_market_order("Buy", qty)

    def sell(self, qty, price=None, stop_loss=None, take_profit=None):
        if price:
            return self.client.place_limit_order("Sell", qty, price)
        else:
            return self.client.place_market_order("Sell", qty)

    def get_balance(self) -> float:
        return self.client.get_usdt_balance()

    def get_position(self) -> Optional[Dict[str, Any]]:
        return self.client.get_open_position()

    def log(self, message: str):
        print(f"[LIVE] {message}")

# ---------------------------------------------------------
# Backtest Context (The Logic Fix)
# ---------------------------------------------------------
class BacktestContext(IContext):
    def __init__(self, initial_balance=10000, fee_rate=0.0):
        self.balance = initial_balance
        self.fee_rate = fee_rate  
        self.leverage = 1  # Default Leverage
        self.position = None 
        self.trades = []
        self.current_price = 0.0
        self.current_time = None
    
    def update_state(self, price: float, time):
        self.current_price = price
        self.current_time = time

    def set_leverage(self, leverage: int):
        """Sets leverage for simulation math."""
        self.leverage = leverage

    def buy(self, qty: float, price: float = None, stop_loss=None, take_profit=None):
        exec_price = price if price else self.current_price
        
        # 1. Calculate Total Contract Value
        total_value = qty * exec_price
        
        # 2. Calculate Required Margin (Cost = Value / Leverage)
        required_margin = total_value / self.leverage
        
        # 3. Calculate Fees (Fees are usually based on Total Value, not Margin)
        fee = total_value * self.fee_rate
        total_cost = required_margin + fee

        # Check if we have enough wallet balance for Margin + Fee
        if self.balance < total_cost:
            self.log(f"Insufficient balance. Need: ${total_cost:.2f}, Have: ${self.balance:.2f} (Lev: {self.leverage}x)")
            return None

        # Logic: Flip Position (Close Sell then Open Buy)
        if self.position and self.position['side'] == 'Sell':
            self._close_position(exec_price)

        # Open Position
        if not self.position:
            self.position = {
                'side': 'Buy', 
                'qty': qty, 
                'entry_price': exec_price,
                'margin_used': required_margin # Store margin to return it later
            }
        else:
            # Average Entry Logic
            old_qty = self.position['qty']
            old_margin = self.position['margin_used']
            
            new_qty = old_qty + qty
            # Weighted Average Price
            avg_price = ((old_qty * self.position['entry_price']) + (qty * exec_price)) / new_qty
            
            self.position['qty'] = new_qty
            self.position['entry_price'] = avg_price
            self.position['margin_used'] = old_margin + required_margin
            
        # Deduct Margin and Fee from Wallet
        self.balance -= total_cost
        
        self.trades.append({'type': 'Buy', 'price': exec_price, 'qty': qty, 'time': self.current_time})
        return "BT_ID"

    def sell(self, qty: float, price: float = None, stop_loss=None, take_profit=None):
        exec_price = price if price else self.current_price
        
        # Logic: If Buy exists, Close it
        if self.position and self.position['side'] == 'Buy':
            self._close_position(exec_price)
            return "BT_ID"
            
        # Short Selling Logic (For Future)
        # Similar to Buy but 'side': 'Sell'
        return None

    def _close_position(self, exit_price: float):
        if not self.position: return
        
        entry = self.position['entry_price']
        qty = self.position['qty']
        margin_used = self.position.get('margin_used', (qty * entry)/self.leverage)
        
        # 1. Calculate PnL
        raw_pnl = (exit_price - entry) * qty
        if self.position['side'] == 'Sell':
            raw_pnl = (entry - exit_price) * qty
            
        # 2. Calculate Exit Fee
        exit_value = qty * exit_price
        fee = exit_value * self.fee_rate
        
        # 3. Net PnL
        net_pnl = raw_pnl - fee
        
        # 4. Return Margin + Net PnL to Wallet
        # We give back the margin we locked, plus the profit (or minus loss)
        self.balance += margin_used + net_pnl
        
        self.trades.append({'type': 'Close', 'price': exit_price, 'pnl': net_pnl, 'time': self.current_time})
        self.position = None

    def get_balance(self) -> float:
        return self.balance

    def get_position(self) -> Optional[Dict[str, Any]]:
        return self.position

    def log(self, message: str):
        pass