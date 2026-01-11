import os
import logging
import json
import numpy as np
from scipy.stats import norm
from enum import Enum
from typing import List, Dict, Set, Optional, Any
from datetime import datetime

# ==========================================
# 1. Logging Setup
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
# 2. Enums
# ==========================================

class ExecutorState(str, Enum):
    PENDING_ENTRY = "PENDING_ENTRY"
    PLACED_ENTRY = "PLACED_ENTRY"
    FILLED_WAIT = "FILLED_WAIT"
    PLACED_EXIT = "PLACED_EXIT"
    COMPLETED = "COMPLETED"

# ==========================================
# 3. PositionExecutor Class
# ==========================================

class PositionExecutor:
    """
    Manages the lifecycle of a single trade:
    Entry -> Verify Fill -> Exit -> Verify Fill -> Complete/Loop.
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

        # Internal State
        self.state: ExecutorState = ExecutorState.PENDING_ENTRY
        self.active_order_id: Optional[str] = None
        
        # PnL Tracking
        self.entry_fill_price: float = 0.0
        self.exit_fill_price: float = 0.0

    def execute_cycle(
        self, 
        current_price: float, 
        open_order_ids: Set[str], 
        order_history_map: Dict[str, Any]
    ) -> ExecutorState:
        
        # ----------------------------------------------------
        # PHASE A: ENTRY LOGIC
        # ----------------------------------------------------
        if self.state == ExecutorState.PENDING_ENTRY:
            limit_price = self.target_entry
            if current_price < self.target_entry:
                limit_price = current_price - self.maker_offset_buy
            
            try:
                ops_logger.debug(f"Attempting Entry | Target: {self.target_entry} | Current: {current_price} | Limit: {limit_price}")
                
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
                ops_logger.warning(f"Entry Placement Failed (likely PostOnly collision): {e}")

        elif self.state == ExecutorState.PLACED_ENTRY:
            # Check if order is still open
            if self.active_order_id not in open_order_ids:
                # It vanished from OPEN orders. Lookup in HISTORY MAP (Passed from Manager).
                order_data = order_history_map.get(self.active_order_id)
                
                if order_data:
                    status = order_data.get('status', '')
                    if status == 'Filled':
                        ops_logger.info(f"Entry Order {self.active_order_id} CONFIRMED FILLED.")
                        self.entry_fill_price = float(order_data.get('avg_price', self.target_entry))
                        self.active_order_id = None
                        self.state = ExecutorState.FILLED_WAIT
                    elif status in ['Cancelled', 'Rejected', 'Deactivated']:
                        ops_logger.warning(f"Entry Order {self.active_order_id} was {status}. Retrying.")
                        self.active_order_id = None
                        self.state = ExecutorState.PENDING_ENTRY
                else:
                    # Not in Open, Not in History -> Latency. Wait.
                    ops_logger.debug(f"Entry Order {self.active_order_id} invisible (Latency). Waiting...")

        # ----------------------------------------------------
        # PHASE B: EXIT LOGIC
        # ----------------------------------------------------
        elif self.state == ExecutorState.FILLED_WAIT:
            limit_price = self.target_exit
            if current_price > self.target_exit:
                limit_price = current_price + self.maker_offset_sell
                
            try:
                ops_logger.debug(f"Attempting Exit | Target: {self.target_exit} | Current: {current_price} | Limit: {limit_price}")
                
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
                error_msg = str(e)
                if "110017" in error_msg or "reduceOnly" in error_msg or "truncated to zero" in error_msg:
                    ops_logger.warning(f"PHANTOM FILL DETECTED: Entry was likely cancelled. Resetting to Entry. Error: {e}")
                    self.state = ExecutorState.PENDING_ENTRY
                    self.active_order_id = None
                else:
                    ops_logger.warning(f"Exit Placement Failed: {e}")

        elif self.state == ExecutorState.PLACED_EXIT:
            # Check if order is still open
            if self.active_order_id not in open_order_ids:
                order_data = order_history_map.get(self.active_order_id)
                
                if order_data:
                    status = order_data.get('status', '')
                    if status == 'Filled':
                        ops_logger.info(f"Exit Order {self.active_order_id} CONFIRMED FILLED. Trade Complete.")
                        self.exit_fill_price = float(order_data.get('avg_price', self.target_exit))
                        self._log_pnl()
                        
                        if self.loop_trade:
                            ops_logger.info("Looping Trade: Resetting to PENDING_ENTRY.")
                            self.state = ExecutorState.PENDING_ENTRY
                            self.active_order_id = None
                            self.entry_fill_price = 0.0
                            self.exit_fill_price = 0.0
                        else:
                            self.state = ExecutorState.COMPLETED
                    elif status in ['Cancelled', 'Rejected', 'Deactivated']:
                        ops_logger.warning(f"Exit Order {self.active_order_id} {status}. Retrying.")
                        self.active_order_id = None
                        self.state = ExecutorState.FILLED_WAIT
                else:
                    # Latency wait
                    ops_logger.debug(f"Exit Order {self.active_order_id} invisible (Latency). Waiting...")

        return self.state

    def _log_pnl(self):
        pnl = (self.exit_fill_price - self.entry_fill_price) * self.qty
        msg = f"TRADE CLOSED | Entry: {self.entry_fill_price:.2f} | Exit: {self.exit_fill_price:.2f} | PnL: {pnl:.4f} USDT"
        pnl_logger.info(msg)

    # --- Serialization ---
    def to_dict(self) -> Dict[str, Any]:
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
# 4. TradeManager Class
# ==========================================

class TradeManager:
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
        ops_logger.info(f"New Executor added: Entry={target_entry}, Loop={loop_trade}")

    # ------------------------------------------------------------------
    # BULK TRADER GENERATION METHODS
    # ------------------------------------------------------------------

    def create_linear_traders(
        self, 
        min_price: float, 
        max_price: float, 
        num_traders: int, 
        qty: float, 
        profit_pct: float, 
        loop_trade: bool = False
    ):
        entries = np.linspace(min_price, max_price, num_traders)
        ops_logger.info(f"--- Generating {num_traders} LINEAR trades ---")
        self._add_bulk_trades(entries, profit_pct, qty, loop_trade)

    def create_normal_traders(
        self, 
        min_price: float, 
        max_price: float, 
        num_traders: int, 
        qty: float, 
        profit_pct: float, 
        loop_trade: bool = False,
        mean_price: Optional[float] = None,
        sigma_factor: float = 6.0
    ):
        loc = mean_price if mean_price is not None else (min_price + max_price) / 2
        scale = (max_price - min_price) / sigma_factor
        probabilities = np.linspace(0.01, 0.99, num_traders)
        entries = norm.ppf(probabilities, loc=loc, scale=scale)
        entries = np.clip(entries, min_price, max_price)
        
        ops_logger.info(f"--- Generating {num_traders} NORMAL trades (Mean: {loc}, SigmaFactor: {sigma_factor}) ---")
        self._add_bulk_trades(entries, profit_pct, qty, loop_trade)

    def _add_bulk_trades(self, entries: np.ndarray, profit_pct: float, qty: float, loop_trade: bool):
        for entry in entries:
            entry_price = float(round(entry, 5))
            markup = 1 + (profit_pct / 100.0)
            exit_price = round(entry_price * markup, 5)
                
            self.add_trade(
                target_entry=entry_price, 
                target_exit=exit_price, 
                qty=qty, 
                loop_trade=loop_trade
            )

    # ------------------------------------------------------------------
    # CORE LOGIC
    # ------------------------------------------------------------------

    def process_tick(self):
        if not self.executors:
            return

        try:
            ops_logger.debug("Tick Start")
            
            # 1. Fetch Market Data
            current_price = self.client.get_current_price()
            open_orders_raw = self.client.get_open_orders()
            
            # 2. Fetch History (Optimized: Once per tick, limit 200)
            history_raw = self.client.get_order_history(limit=200)
            
            # 3. Create Lookups (O(1) access)
            active_order_ids: Set[str] = {o['order_id'] for o in open_orders_raw}
            history_map: Dict[str, Any] = {o['order_id']: o for o in history_raw}
            
            active_executors: List[PositionExecutor] = []
            
            # 4. Delegate to Executors with new history map
            for executor in self.executors:
                status = executor.execute_cycle(
                    current_price=current_price, 
                    open_order_ids=active_order_ids, 
                    order_history_map=history_map
                )
                
                if status != ExecutorState.COMPLETED:
                    active_executors.append(executor)
                else:
                    ops_logger.info("Executor cleanup: Removed completed trade.")
            
            self.executors = active_executors
            
        except Exception as e:
            ops_logger.error(f"Critical Error in process_tick: {e}")

    # --- Persistence ---

    def save_to_disk(self, filename: str = "trader_state.json"):
        try:
            data = [exc.to_dict() for exc in self.executors]
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            ops_logger.info(f"State saved to {filename} ({len(data)} executors)")
        except Exception as e:
            ops_logger.error(f"Failed to save state: {e}")

    def load_from_disk(self, filename: str = "trader_state.json"):
        if not os.path.exists(filename):
            ops_logger.warning(f"Save file {filename} not found.")
            return

        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.executors = []
            for entry in data:
                executor = PositionExecutor.from_dict(entry, self.client)
                self.executors.append(executor)
            
            ops_logger.info(f"State loaded from {filename}. Restored {len(self.executors)} executors.")
        except Exception as e:
            ops_logger.error(f"Failed to load state: {e}")
