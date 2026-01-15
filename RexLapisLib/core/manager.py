import os
import logging
import json
import numpy as np
from scipy.stats import norm
from typing import List, Dict, Set, Optional, Any

# Relative import from the models sub-package
from ..models.states import ExecutorState

# ==========================================
# 1. Logging Configuration
# ==========================================
# Logs are stored in a local ./results directory
os.makedirs("./results", exist_ok=True)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# OPS Logger: For technical operations and errors
ops_logger = logging.getLogger("OPS")
ops_logger.setLevel(logging.DEBUG)
ops_handler = logging.FileHandler("./results/ops.log")
ops_handler.setFormatter(file_formatter)
ops_logger.addHandler(ops_handler)

# PNL Logger: Dedicated to tracking financial outcomes
pnl_logger = logging.getLogger("PNL")
pnl_logger.setLevel(logging.INFO)
pnl_handler = logging.FileHandler("./results/pnl.log")
pnl_handler.setFormatter(file_formatter)
pnl_logger.addHandler(pnl_handler)

# ==========================================
# 2. PositionExecutor Class
# ==========================================
class PositionExecutor:
    """
    Manages the lifecycle of a single trade:
    PENDING -> PLACED_ENTRY -> FILLED_WAIT -> PLACED_EXIT -> COMPLETED.
    """

    def __init__(
        self, 
        client: Any, 
        target_entry: float, 
        target_exit: float, 
        qty: float, 
        maker_offset_buy: float, 
        maker_offset_sell: float,
        loop_trade: bool = False
    ):
        self.client = client
        self.target_entry = target_entry
        self.target_exit = target_exit
        self.qty = qty
        self.maker_offset_buy = maker_offset_buy
        self.maker_offset_sell = maker_offset_sell
        self.loop_trade = loop_trade

        # Operational State
        self.state: ExecutorState = ExecutorState.PENDING_ENTRY
        self.active_order_id: Optional[str] = None
        
        # Performance Tracking
        self.entry_fill_price: float = 0.0
        self.exit_fill_price: float = 0.0

    def execute_cycle(
        self, 
        current_price: float, 
        open_order_ids: Set[str], 
        order_history_map: Dict[str, Any]
    ) -> ExecutorState:
        """Processes a single heartbeat for this specific trade."""
        
        # --- PHASE A: ENTRY (BUYING) ---
        if self.state == ExecutorState.PENDING_ENTRY:
            limit_price = self.target_entry
            # Adjust limit price to ensure we stay as a Maker
            if current_price < self.target_entry:
                limit_price = current_price - self.maker_offset_buy
            
            try:
                self.active_order_id = self.client.place_limit_order(
                    side="Buy",
                    qty=self.qty,
                    price=limit_price,
                    reduce_only=False,
                    post_only=True 
                )
                ops_logger.info(f"Entry Placed | ID: {self.active_order_id}")
                self.state = ExecutorState.PLACED_ENTRY
            except Exception as e:
                ops_logger.warning(f"Entry placement failed (likely PostOnly collision): {e}")

        elif self.state == ExecutorState.PLACED_ENTRY:
            if self.active_order_id not in open_order_ids:
                order_data = order_history_map.get(self.active_order_id)
                if order_data:
                    status = order_data.get('status', '')
                    if status == 'Filled':
                        ops_logger.info(f"Entry Order {self.active_order_id} filled.")
                        self.entry_fill_price = float(order_data.get('avg_price', self.target_entry))
                        self.active_order_id = None
                        self.state = ExecutorState.FILLED_WAIT
                    elif status in ['Cancelled', 'Rejected', 'Deactivated']:
                        self.active_order_id = None
                        self.state = ExecutorState.PENDING_ENTRY

        # --- PHASE B: EXIT (SELLING) ---
        elif self.state == ExecutorState.FILLED_WAIT:
            limit_price = self.target_exit
            if current_price > self.target_exit:
                limit_price = current_price + self.maker_offset_sell
                
            try:
                self.active_order_id = self.client.place_limit_order(
                    side="Sell",
                    qty=self.qty,
                    price=limit_price,
                    reduce_only=True,
                    post_only=True
                )
                ops_logger.info(f"Exit Placed | ID: {self.active_order_id}")
                self.state = ExecutorState.PLACED_EXIT
            except Exception as e:
                # Handle cases where the position was closed manually or incorrectly
                if "110017" in str(e) or "reduceOnly" in str(e):
                    ops_logger.warning("Reduce-only error: Entry likely cancelled. Resetting.")
                    self.state = ExecutorState.PENDING_ENTRY
                    self.active_order_id = None
                else:
                    ops_logger.warning(f"Exit placement failed: {e}")

        elif self.state == ExecutorState.PLACED_EXIT:
            if self.active_order_id not in open_order_ids:
                order_data = order_history_map.get(self.active_order_id)
                if order_data:
                    status = order_data.get('status', '')
                    if status == 'Filled':
                        ops_logger.info(f"Exit Order {self.active_order_id} filled. Trade Complete.")
                        self.exit_fill_price = float(order_data.get('avg_price', self.target_exit))
                        self._log_pnl()
                        
                        if self.loop_trade:
                            self.state = ExecutorState.PENDING_ENTRY
                            self.active_order_id = None
                            self.entry_fill_price = 0.0
                            self.exit_fill_price = 0.0
                        else:
                            self.state = ExecutorState.COMPLETED
                    elif status in ['Cancelled', 'Rejected', 'Deactivated']:
                        self.active_order_id = None
                        self.state = ExecutorState.FILLED_WAIT

        return self.state

    def _log_pnl(self):
        """Calculates and logs the PnL of the completed cycle."""
        pnl = (self.exit_fill_price - self.entry_fill_price) * self.qty
        pnl_logger.info(f"CLOSED | Entry: {self.entry_fill_price} | Exit: {self.exit_fill_price} | PnL: {pnl:.4f} USDT")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the executor for JSON storage or Web API."""
        return {
            "target_entry": self.target_entry,
            "target_exit": self.target_exit,
            "qty": self.qty,
            "maker_offset_buy": self.maker_offset_buy,
            "maker_offset_sell": self.maker_offset_sell,
            "loop_trade": self.loop_trade,
            "state": self.state.value,
            "active_order_id": self.active_order_id,
            "entry_fill_price": self.entry_fill_price
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: Any) -> 'PositionExecutor':
        """Reconstructs an executor from saved state."""
        instance = cls(
            client=client,
            target_entry=data["target_entry"],
            target_exit=data["target_exit"],
            qty=data["qty"],
            maker_offset_buy=data["maker_offset_buy"],
            maker_offset_sell=data["maker_offset_sell"],
            loop_trade=data.get("loop_trade", False)
        )
        instance.state = ExecutorState(data["state"])
        instance.active_order_id = data["active_order_id"]
        instance.entry_fill_price = data.get("entry_fill_price", 0.0)
        return instance

# ==========================================
# 3. TradeManager Class
# ==========================================
class TradeManager:
    """
    Orchestrates multiple PositionExecutors and handles 
    bulk strategy generation.
    """
    def __init__(self, client: Any, maker_offset_buy: float, maker_offset_sell: float):
        self.client = client
        self.maker_offset_buy = maker_offset_buy
        self.maker_offset_sell = maker_offset_sell
        self.executors: List[PositionExecutor] = []
        ops_logger.info("TradeManager Initialized")

    def add_trade(self, target_entry: float, target_exit: float, qty: float, loop_trade: bool = False):
        executor = PositionExecutor(
            client=self.client,
            target_entry=target_entry,
            target_exit=target_exit,
            qty=qty,
            maker_offset_buy=self.maker_offset_buy,
            maker_offset_sell=self.maker_offset_sell,
            loop_trade=loop_trade
        )
        self.executors.append(executor)

    def create_linear_traders(self, min_p: float, max_p: float, count: int, qty: float, profit: float, loop: bool = False):
        """Generates trades at equally spaced price intervals."""
        entries = np.linspace(min_p, max_p, count)
        self._add_bulk_trades(entries, profit, qty, loop)

    def create_normal_traders(self, min_p: float, max_p: float, count: int, qty: float, profit: float, loop: bool = False, mean: float = None, sigma: float = 6.0):
        """Generates trades based on a Gaussian distribution."""
        loc = mean if mean is not None else (min_p + max_p) / 2
        scale = (max_p - min_p) / sigma
        probabilities = np.linspace(0.01, 0.99, count)
        entries = norm.ppf(probabilities, loc=loc, scale=scale)
        entries = np.clip(entries, min_p, max_p)
        self._add_bulk_trades(entries, profit, qty, loop)

    def _add_bulk_trades(self, entries: np.ndarray, profit_pct: float, qty: float, loop: bool):
        for entry in entries:
            entry_price = float(round(entry, 5))
            markup = 1 + (profit_pct / 100.0)
            exit_price = round(entry_price * markup, 5)
            self.add_trade(entry_price, exit_price, qty, loop)

    def process_tick(self):
        """Main heartbeat logic called every few seconds."""
        if not self.executors:
            return

        try:
            # 1. Synchronize data with the exchange
            current_price = self.client.get_current_price()
            open_orders_raw = self.client.get_open_orders()
            history_raw = self.client.get_order_history(limit=200)
            
            # 2. Map data for O(1) performance lookup
            active_ids: Set[str] = {o['order_id'] for o in open_orders_raw}
            h_map: Dict[str, Any] = {o['order_id']: o for o in history_raw}
            
            # 3. Execute logic for each trader and clean up completed ones
            active_executors = []
            for executor in self.executors:
                status = executor.execute_cycle(current_price, active_ids, h_map)
                if status != ExecutorState.COMPLETED:
                    active_executors.append(executor)
            
            self.executors = active_executors
        except Exception as e:
            ops_logger.error(f"Tick Failure: {e}")

    def get_ui_data(self) -> List[Dict[str, Any]]:
        """Provides a JSON-serializable summary for Web Dashboards."""
        return [executor.to_dict() for executor in self.executors]

    def save_to_disk(self, filename: str = "trader_state.json"):
        """Saves session to JSON to prevent data loss on crash."""
        try:
            data = self.get_ui_data()
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            ops_logger.error(f"Save failure: {e}")

    def load_from_disk(self, filename: str = "trader_state.json"):
        """Restores session from JSON."""
        if not os.path.exists(filename):
            return
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            self.executors = [PositionExecutor.from_dict(entry, self.client) for entry in data]
            ops_logger.info(f"Restored {len(self.executors)} executors.")
        except Exception as e:
            ops_logger.error(f"Load failure: {e}")