from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd
import time

class IContext(ABC):
    """Unified Interface for Strategy Interaction."""
    
    @abstractmethod
    def set_leverage(self, leverage: int):
        pass

    @abstractmethod
    def buy(self, qty: float, price: float = None, post_only: bool = False, reduce_only: bool = False, **kwargs):
        pass

    @abstractmethod
    def sell(self, qty: float, price: float = None, post_only: bool = False, reduce_only: bool = False, **kwargs):
        pass

    @abstractmethod
    def get_balance(self) -> float:
        pass

    @abstractmethod
    def get_position(self) -> Optional[Dict[str, Any]]:
        pass

    @property
    @abstractmethod
    def pending_orders(self) -> List[Dict]:
        """Returns a list of active open orders."""
        pass

    @abstractmethod
    def log(self, message: str):
        pass

# =========================================================
# 1. LIVE CONTEXT (Fixed: Bridges Strategy to Exchange)
# =========================================================
class LiveContext(IContext):
    def __init__(self, client):
        self.client = client
        self._last_sync_time = 0

    @property
    def pending_orders(self) -> List[Dict]:
        """
        CRITICAL FIX: Fetches real open orders from Bybit.
        This allows the strategy to check 'self.ctx.pending_orders' without crashing.
        """
        return self.client.get_open_orders()

    def _ensure_sync(self):
        """Forces a refresh if data is stale (Resilience feature)."""
        current_time = time.time()
        if current_time - self._last_sync_time > 30:
            self._last_sync_time = current_time
    
    def set_leverage(self, leverage: int):
        self.client.setup_bot(leverage) 

    def buy(self, qty, price=None, post_only=False, reduce_only=False, **kwargs):
        if price:
            return self.client.place_limit_order("Buy", qty, price, reduce_only=reduce_only, post_only=post_only)
        else:
            return self.client.place_market_order("Buy", qty, reduce_only=reduce_only)
        
    def sell(self, qty, price=None, post_only=False, reduce_only=False, **kwargs):
        if price:
            return self.client.place_limit_order("Sell", qty, price, reduce_only=reduce_only, post_only=post_only)
        else:
            return self.client.place_market_order("Sell", qty, reduce_only=reduce_only)
        
    def get_balance(self) -> float:
        self._ensure_sync()
        return self.client.get_usdt_balance()

    def get_position(self) -> Optional[Dict[str, Any]]:
        self._ensure_sync()
        return self.client.get_open_position()

    def log(self, message: str):
        print(f"[LIVE] {message}")

# =========================================================
# 2. BACKTEST CONTEXT (Preserved: Full Simulation Logic)
# =========================================================
# =========================================================
# 2. BACKTEST CONTEXT (FIXED)
# =========================================================
class BacktestContext(IContext):
    def __init__(self, initial_balance: float = 10000, fee_rate: float = 0.0006):
        self.balance = initial_balance
        self.fee_rate = fee_rate
        self.leverage = 1 
        self.position = None 
        self.trades = []
        self._pending_orders = [] 
        self.current_price = 0.0
        self.current_time = None

    def update_state(self, price: float, time, candle: pd.Series = None):
        """Updates internal state and checks for Limit fills."""
        self.current_price = price
        self.current_time = time
        
        if candle is not None:
            self._check_pending_orders(candle)

    def set_leverage(self, leverage: int):
        self.leverage = leverage

    @property
    def pending_orders(self) -> List[Dict]:
        return self._pending_orders

    def buy(self, qty: float, price: float = None, post_only: bool = False, reduce_only: bool = False, **kwargs):
        # 1. Post-Only Check
        if post_only and price and price >= self.current_price:
            self.log(f"REJECTED: Post-Only Buy Limit ({price}) is Taker (Market: {self.current_price})")
            return None

        # 2. Reduce-Only Check
        if reduce_only and (not self.position or self.position['side'] != 'Sell'):
            self.log("REJECTED: Reduce-Only Buy requested without a Short position.")
            return None

        # 3. Limit Order Logic
        if price and price < self.current_price:
            self._pending_orders.append({
                'side': 'Buy', 'qty': qty, 'price': price, 
                'post_only': post_only, 'reduce_only': reduce_only
            })
            return "BT_PENDING"

        # 4. Immediate Execution
        exec_price = price if price else self.current_price
        return self._execute_buy(qty, exec_price, reduce_only)

    def sell(self, qty: float, price: float = None, post_only: bool = False, reduce_only: bool = False, **kwargs):
        # 1. Post-Only Check
        if post_only and price and price <= self.current_price:
            self.log(f"REJECTED: Post-Only Sell Limit ({price}) is Taker (Market: {self.current_price})")
            return None

        # 2. Reduce-Only Check
        if reduce_only and (not self.position or self.position['side'] != 'Buy'):
            self.log("REJECTED: Reduce-Only Sell requested without a Long position.")
            return None

        # 3. Limit Order Logic
        if price and price > self.current_price:
            self._pending_orders.append({
                'side': 'Sell', 'qty': qty, 'price': price, 
                'post_only': post_only, 'reduce_only': reduce_only
            })
            return "BT_PENDING"

        # 4. Immediate Execution
        exec_price = price if price else self.current_price
        return self._execute_sell(qty, exec_price, reduce_only)

    def _execute_buy(self, qty: float, exec_price: float, reduce_only: bool):
        total_value = qty * exec_price
        required_margin = total_value / self.leverage
        fee = total_value * self.fee_rate
        total_cost = required_margin + fee

        if self.balance < total_cost:
            self.log(f"INSUFFICIENT BALANCE: Need ${total_cost:.2f}, Have ${self.balance:.2f}")
            return None

        if self.position and self.position['side'] == 'Sell':
            self._close_position(exec_price)
            if reduce_only: return "BT_CLOSE"

        if not self.position:
            self.position = {
                'side': 'Buy', 'qty': qty, 'entry_price': exec_price, 'margin_used': required_margin
            }
        else:
            old_qty = self.position['qty']
            old_margin = self.position['margin_used']
            new_qty = old_qty + qty
            avg_price = ((old_qty * self.position['entry_price']) + (qty * exec_price)) / new_qty
            self.position.update({'qty': new_qty, 'entry_price': avg_price, 'margin_used': old_margin + required_margin})

        self.balance -= total_cost
        self.trades.append({'type': 'Buy', 'price': exec_price, 'qty': qty, 'time': self.current_time})
        return "BT_ID"

    def _execute_sell(self, qty: float, exec_price: float, reduce_only: bool):
        if self.position and self.position['side'] == 'Buy':
            self._close_position(exec_price)
            return "BT_ID"
        if reduce_only: return None
        return None

    def _check_pending_orders(self, candle: pd.Series):
        for order in self._pending_orders[:]:
            if order['side'] == 'Buy' and candle['low'] <= order['price']:
                self.log(f"LIMIT FILL: Buy {order['qty']} at {order['price']}")
                self._execute_buy(order['qty'], order['price'], order['reduce_only'])
                self._pending_orders.remove(order)
            elif order['side'] == 'Sell' and candle['high'] >= order['price']:
                self.log(f"LIMIT FILL: Sell {order['qty']} at {order['price']}")
                self._execute_sell(order['qty'], order['price'], order['reduce_only'])
                self._pending_orders.remove(order)

    def _close_position(self, exit_price: float):
        if not self.position: return
        entry = self.position['entry_price']
        qty = self.position['qty']
        margin_used = self.position['margin_used']
        
        raw_pnl = (exit_price - entry) * qty if self.position['side'] == 'Buy' else (entry - exit_price) * qty
        fee = (qty * exit_price) * self.fee_rate
        net_pnl = raw_pnl - fee
        
        self.balance += margin_used + net_pnl
        self.trades.append({'type': 'Close', 'price': exit_price, 'pnl': net_pnl, 'time': self.current_time})
        self.position = None

    def get_balance(self) -> float:
        return self.balance

    def get_position(self) -> Optional[Dict[str, Any]]:
        return self.position

    def log(self, message: str):
        print(f"[{self.current_time}] SIM: {message}")