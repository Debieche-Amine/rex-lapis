The `TradeManager` coordinates multiple trading strategies (`PositionExecutors`), handles data fetching, and manages state persistence.

## Class: `TradeManager`

### Initialization
```python
TradeManager(client: Any, maker_offset_buy: float, maker_offset_sell: float)
```
*   **`client`**: Instance of the Bybit `Client` wrapper.
*   **`maker_offset_buy`**: Distance below current price to place limit bids (to ensure Maker status).
*   **`maker_offset_sell`**: Distance above current price to place limit asks (to ensure Maker status).

---

### Core Methods

#### `add_trade(...)`
Registers a new isolated trade plan.
```python
def add_trade(self, target_entry: float, target_exit: float, qty: float, loop_trade: bool = False)
```
*   **`target_entry`**: Maximum price willing to pay. If market is lower, logic lowers bid to save money.
*   **`target_exit`**: Minimum price willing to sell. If market is higher, logic raises ask to increase profit.
*   **`qty`**: Order size.
*   **`loop_trade`**: If `True`, the trade resets to `PENDING_ENTRY` immediately after completion. If `False`, it dies after one cycle.

#### `process_tick()`
The main loop heartbeat. Fetches market data once and updates all active trades.
```python
def process_tick(self)
```

#### `stop_all_entries()`
Cancels all open Buy orders and prevents new entries. Existing open positions (filled buys) are allowed to close naturally.
```python
def stop_all_entries(self)
```

---

### Persistence Methods

#### `save_to_disk(...)`
Serializes the state of all executors to a JSON file.
```python
def save_to_disk(self, filename: str = "trader_state.json")
```

#### `load_from_disk(...)`
Clears current memory and reconstructs executors from a JSON file.
```python
def load_from_disk(self, filename: str = "trader_state.json")
```
