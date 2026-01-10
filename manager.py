import os
import logging
import json
from enum import Enum, auto
from typing import List, Dict, Set, Optional, Any
from datetime import datetime

# ==========================================
# 1. Logging Setup (Same as before)
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
    # Using str mixin for easier JSON serialization
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
    Entry -> Verification -> Fill -> Exit -> Verification -> Fill -> Complete/Loop.
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
        self.is_order_confirmed_active: bool = False
        self.stop_requested: bool = False
        
        # PnL Tracking
        self.entry_fill_price: float = 0.0
        self.exit_fill_price: float = 0.0

    def abort_entry(self):
        """
        Called by Manager during shutdown. 
        Cancels open Buy orders or prevents new ones. 
        Does NOT affect open positions (FILLED_WAIT/PLACED_EXIT).
        """
        self.stop_requested = True
        
        if self.state == ExecutorState.PENDING_ENTRY:
            # Stop immediately
            self.state = ExecutorState.COMPLETED
            ops_logger.info("Executor stopped before placing entry.")
            
        elif self.state == ExecutorState.PLACED_ENTRY and self.active_order_id:
            # Cancel the active buy order
            try:
                ops_logger.info(f"Shutdown requested: Canceling Entry Order {self.active_order_id}")
                # Assuming client has a method to cancel a specific order, 
                # or we use cancel_all if ID specific isn't available, but prompt implies specific.
                # Since client wrapper in prompt documentation only has 'cancel_all_orders', 
                # we might have to use that via manager, but usually wrappers support specific cancel.
                # Assuming standard pybit wrapper behavior or custom implementation:
                # If the wrapper ONLY has cancel_all_orders(), this line is pseudo-code for a specific cancel.
                # Given the prompt, let's assume we can cancel specifically or just leave it to expire if wrapper limits us.
                # However, for this exercise, we will assume a specific cancel method exists or we handle it gracefully.
                # *Self-correction based on prompt doc:* The prompt doc says "cancel_all_orders()" but usually wrappers allow ID.
                # If we strictly follow the doc provided in prompt 1, we might not be able to cancel single orders easily.
                # But typically, a 'cancel_order(order_id)' is standard. I will assume it exists or I log a warning.
                if hasattr(self.client, 'cancel_order'):
                    self.client.cancel_order(symbol=self.client.symbol, orderId=self.active_order_id)
                else:
                    ops_logger.warning("Client wrapper missing 'cancel_order(id)'. Manual cancellation required.")
                    
            except Exception as e:
                ops_logger.error(f"Failed to cancel entry order {self.active_order_id}: {e}")
            
            self.state = ExecutorState.COMPLETED

    def execute_cycle(self, current_price: float, open_order_ids: Set[str]) -> ExecutorState:
        # If stopped and we are just waiting to start, die.
        if self.stop_requested and self.state == ExecutorState.PENDING_ENTRY:
            return ExecutorState.COMPLETED

        # ----------------------------------------------------
        # PHASE A: ENTRY LOGIC
        # ----------------------------------------------------
        if self.state == ExecutorState.PENDING_ENTRY:
            limit_price = self.target_entry
            
            # Optimized Entry Logic (Lower bid if market is better)
            if current_price < self.target_entry:
                limit_price = current_price - self.maker_offset_buy
            
            try:
                # Check stop request again before API call
                if self.stop_requested: return ExecutorState.COMPLETED

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
                self.is_order_confirmed_active = False 
                
            except Exception as e:
                ops_logger.error(f"Entry Placement Failed: {e}")

        elif self.state == ExecutorState.PLACED_ENTRY:
            if self.active_order_id in open_order_ids:
                if not self.is_order_confirmed_active:
                    self.is_order_confirmed_active = True
            else:
                if self.is_order_confirmed_active:
                    ops_logger.info(f"Entry Order {self.active_order_id} Vanished. Assuming FILLED.")
                    self.entry_fill_price = current_price
                    self.active_order_id = None
                    self.state = ExecutorState.FILLED_WAIT
                else:
                    ops_logger.warning(f"Entry Order rejected. Retrying.")
                    self.state = ExecutorState.PENDING_ENTRY
                    self.active_order_id = None

        # ----------------------------------------------------
        # PHASE B: EXIT LOGIC
        # ----------------------------------------------------
        elif self.state == ExecutorState.FILLED_WAIT:
            limit_price = self.target_exit
            
            # Optimized Exit Logic (Higher ask if market is better)
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
                self.is_order_confirmed_active = False 
                
            except Exception as e:
                ops_logger.error(f"Exit Placement Failed: {e}")

        elif self.state == ExecutorState.PLACED_EXIT:
            if self.active_order_id in open_order_ids:
                if not self.is_order_confirmed_active:
                    self.is_order_confirmed_active = True
            else:
                if self.is_order_confirmed_active:
                    ops_logger.info(f"Exit Order {self.active_order_id} Vanished. Trade COMPLETE.")
                    self.exit_fill_price = current_price
                    self._log_pnl()
                    
                    # LOOP LOGIC
                    if self.loop_trade and not self.stop_requested:
                        ops_logger.info("Looping Trade: Resetting to PENDING_ENTRY.")
                        self.state = ExecutorState.PENDING_ENTRY
                        self.active_order_id = None
                        self.is_order_confirmed_active = False
                        self.entry_fill_price = 0.0
                        self.exit_fill_price = 0.0
                    else:
                        self.state = ExecutorState.COMPLETED
                else:
                    ops_logger.warning(f"Exit Order rejected. Retrying.")
                    self.state = ExecutorState.FILLED_WAIT
                    self.active_order_id = None

        return self.state

    def _log_pnl(self):
        pnl = (self.exit_fill_price - self.entry_fill_price) * self.qty
        msg = f"TRADE CLOSED | Entry: {self.entry_fill_price:.2f} | Exit: {self.exit_fill_price:.2f} | PnL: {pnl:.4f} USDT"
        pnl_logger.info(msg)

    # --- Serialization Methods ---
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object state to dictionary for JSON saving."""
        return {
            "target_entry": self.target_entry,
            "target_exit": self.target_exit,
            "qty": self.qty,
            "maker_offset_buy": self.maker_offset_buy,
            "maker_offset_sell": self.maker_offset_sell,
            "loop_trade": self.loop_trade,
            "state": self.state.value,
            "active_order_id": self.active_order_id,
            "is_order_confirmed_active": self.is_order_confirmed_active,
            "entry_fill_price": self.entry_fill_price,
            "stop_requested": self.stop_requested
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], client: Any) -> 'PositionExecutor':
        """Reconstruct object from dictionary."""
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
        instance.is_order_confirmed_active = data["is_order_confirmed_active"]
        instance.entry_fill_price = data.get("entry_fill_price", 0.0)
        instance.stop_requested = data.get("stop_requested", False)
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

    def stop_all_entries(self):
        """
        Commands all executors to stop entering new trades.
        Active buy orders are cancelled.
        Open positions (Sell side) remain active to close naturally.
        """
        ops_logger.info("STOP ALL ENTRIES triggered.")
        for executor in self.executors:
            executor.abort_entry()

    def process_tick(self):
        if not self.executors:
            return

        try:
            ops_logger.debug("Tick Start")
            current_price = self.client.get_current_price()
            open_orders_raw = self.client.get_open_orders()
            active_order_ids: Set[str] = {o['order_id'] for o in open_orders_raw}
            
            active_executors: List[PositionExecutor] = []
            
            for executor in self.executors:
                status = executor.execute_cycle(current_price, active_order_ids)
                if status != ExecutorState.COMPLETED:
                    active_executors.append(executor)
                else:
                    ops_logger.info("Executor cleanup: Removed completed trade.")
            
            self.executors = active_executors
            
        except Exception as e:
            ops_logger.error(f"Critical Error in process_tick: {e}")

    # --- Persistence Methods ---

    def save_to_disk(self, filename: str = "trader_state.json"):
        """Saves all active executors to a JSON file."""
        try:
            data = [exc.to_dict() for exc in self.executors]
            with open(filename, 'w') as f:
                json.dump(data, f, indent=4)
            ops_logger.info(f"State saved to {filename} ({len(data)} executors)")
        except Exception as e:
            ops_logger.error(f"Failed to save state: {e}")

    def load_from_disk(self, filename: str = "trader_state.json"):
        """
        Loads executors from disk, replacing current ones.
        Requires the client object to be already initialized in the Manager.
        """
        if not os.path.exists(filename):
            ops_logger.warning(f"Save file {filename} not found.")
            return

        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            self.executors = []
            for entry in data:
                # We reuse the Manager's global offsets if they aren't in the save (backward compatibility)
                # But here we are using the internal offset saved in the executor dict
                executor = PositionExecutor.from_dict(entry, self.client)
                self.executors.append(executor)
            
            ops_logger.info(f"State loaded from {filename}. Restored {len(self.executors)} executors.")
        except Exception as e:
            ops_logger.error(f"Failed to load state: {e}")
