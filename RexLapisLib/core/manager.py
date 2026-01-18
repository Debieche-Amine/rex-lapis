import os
import logging
import json
import numpy as np
from scipy.stats import norm
from typing import List, Dict, Set, Optional, Any

# Relative import from the models sub-package
# Ensure this path exists in your project, otherwise replace with direct Enum definition
try:
    from ..models.states import ExecutorState
except ImportError:
    # Fallback if model file is missing during test
    from enum import Enum
    class ExecutorState(Enum):
        PENDING_ENTRY = "PENDING_ENTRY"
        PLACED_ENTRY = "PLACED_ENTRY"
        FILLED_WAIT = "FILLED_WAIT"
        PLACED_EXIT = "PLACED_EXIT"
        COMPLETED = "COMPLETED"

# ==========================================
# 1. Logging Configuration
# ==========================================
os.makedirs("./results", exist_ok=True)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ops_logger = logging.getLogger("OPS")
ops_logger.setLevel(logging.DEBUG)
ops_handler = logging.FileHandler("./results/ops.log")
ops_handler.setFormatter(file_formatter)
ops_logger.addHandler(ops_handler)

pnl_logger = logging.getLogger("PNL")
pnl_logger.setLevel(logging.INFO)
pnl_handler = logging.FileHandler("./results/pnl.log")
pnl_handler.setFormatter(file_formatter)
pnl_logger.addHandler(pnl_handler)

# ==========================================
# 2. PositionExecutor Class (UNTOUCHED)
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
            "state": self.state.value if isinstance(self.state, ExecutorState) else self.state,
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
        # Handle State Enum reconstruction safely
        state_val = data["state"]
        try:
            instance.state = ExecutorState(state_val)
        except ValueError:
            # Fallback if string doesn't match enum exactly
            instance.state = ExecutorState[state_val] if state_val in ExecutorState.__members__ else ExecutorState.PENDING_ENTRY
            
        instance.active_order_id = data["active_order_id"]
        instance.entry_fill_price = data.get("entry_fill_price", 0.0)
        return instance

# ==========================================
# 3. TradeManager Class (UPDATED FOR RESILIENCE)
# ==========================================
class TradeManager:
    """
    Orchestrates multiple PositionExecutors AND handles single strategy persistence.
    Compatible with both Grid Bots and Single-Strategy Bots (run_live.py).
    """
    def __init__(self, client: Any, state_file: str = "trader_state.json", maker_offset_buy: float = 0.0, maker_offset_sell: float = 0.0):
        self.client = client
        self.state_file = state_file
        self.maker_offset_buy = maker_offset_buy
        self.maker_offset_sell = maker_offset_sell
        self.executors: List[PositionExecutor] = []
        ops_logger.info(f"TradeManager Initialized. Persistence File: {self.state_file}")

    # --- Original Grid Logic Methods (Preserved) ---

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
        """Main heartbeat logic called every few seconds (For Grid Bot)."""
        if not self.executors:
            return

        try:
            current_price = self.client.get_current_price()
            open_orders_raw = self.client.get_open_orders()
            history_raw = self.client.get_order_history(limit=200)
            
            active_ids: Set[str] = {o['order_id'] for o in open_orders_raw}
            h_map: Dict[str, Any] = {o['order_id']: o for o in history_raw}
            
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

    # --- Updated Persistence Logic (Compatible with run_live.py) ---

    def save_state(self, data: Dict[str, Any]):
        """Helper alias required by run_live.py to save dictionary data."""
        self.save_to_disk(data=data)

    def save_to_disk(self, filename: str = None, data: Any = None):
        """
        Saves session to JSON. 
        Supports both:
        1. Single Strategy Data (Passed via 'data')
        2. Grid Executor List (If data is None)
        """
        target_file = filename if filename else self.state_file
        
        try:
            # If explicit data provided (run_live.py), save it.
            # Else, save the list of executors (Grid Bot).
            content = data if data is not None else self.get_ui_data()
            
            with open(target_file, 'w') as f:
                json.dump(content, f, indent=4)
        except Exception as e:
            ops_logger.error(f"Save failure: {e}")

    def load_from_disk(self, filename: str = None):
        """Restores session from JSON."""
        target_file = filename if filename else self.state_file
        
        if not os.path.exists(target_file):
            return None
        try:
            with open(target_file, 'r') as f:
                data = json.load(f)
            
            # Case 1: Data is a List -> It's a Grid Bot State
            if isinstance(data, list):
                self.executors = [PositionExecutor.from_dict(entry, self.client) for entry in data]
                ops_logger.info(f"Restored {len(self.executors)} executors.")
                return self.executors
            
            # Case 2: Data is a Dict -> It's a Single Strategy State (run_live.py)
            return data
            
        except Exception as e:
            ops_logger.error(f"Load failure: {e}")
            return None

    # --- New Resilience Logic (Required by run_live.py) ---

    def has_active_trades(self):
        """Checks if there are active executors OR a saved state file exists."""
        if len(self.executors) > 0:
            return True
        return os.path.exists(self.state_file)

    def clear_state(self):
        """Deletes the state file."""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
            except Exception:
                pass

    def reconcile_after_crash(self):
        """
        The 'Power Outage' fix: Checks if Bybit has a position 
        that matches our last saved state.
        """
        saved_state = self.load_from_disk()
        actual_pos = self.client.get_open_position()
        
        # Scenario 1: We crashed, but position is still open on exchange.
        if actual_pos:
            ops_logger.info(f"Reconcile: Found active position on exchange: {actual_pos['qty']}")
            # If we have saved state, return it combined with actual pos
            if isinstance(saved_state, dict):
                saved_state['position'] = actual_pos
                return saved_state
            return {"position": actual_pos} # Minimal recovery

        # Scenario 2: We have a saved state saying we are open, but exchange says NO.
        # This means TP/SL was hit while we were dead.
        if saved_state and not actual_pos:
            # Check if saved_state implies we *should* have a position
            has_pos_flag = False
            if isinstance(saved_state, dict) and saved_state.get('position'):
                has_pos_flag = True
            elif isinstance(saved_state, list) and len(saved_state) > 0:
                has_pos_flag = True # Grid executors existed
            
            if has_pos_flag:
                ops_logger.info("Reconcile: Position closed while offline. Clearing state.")
                self.clear_state()
                self.executors = [] # Clear grid executors too
        
        return None