# RexLapisLib\core\client.py
import os
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from pybit.exceptions import InvalidRequestError
from pybit.exceptions import ConnectionError, TimeoutError
from pybit.unified_trading import WebSocket
import time
from functools import wraps
import pandas as pd

# Load environment variables
load_dotenv()


def auto_resync(max_retries=5, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    retries += 1
                    wait_time = delay * (2 ** (retries - 1)) 
                    print(f"⚠️ Network Error in {func.__name__}. Retry {retries}/{max_retries} in {wait_time}s...")
                    time.sleep(wait_time)
            raise ConnectionError("❌ Max retries reached. Internet connection lost.")
        return wrapper
    return decorator

class Client:
    def __init__(self, symbol: str, api_key: str, api_secret: str, category: str = "linear", api_endpoint: str = "demo"):
        """
        Initializes the Bybit Client.
        :param category: Use "spot" for XAUTUSDT and "linear" for Futures.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.endpoint_env = api_endpoint.lower()
        self.symbol = symbol.upper()
        self.category = category.lower() 

        if self.endpoint_env == "demo":
            self.testnet = True
            self.http_url = "https://api-demo.bybit.com"
        else:
            self.testnet = False
            self.http_url = "https://api.bybit.com"

        self.session = HTTP(
            testnet=self.testnet, 
            api_key=self.api_key, 
            api_secret=self.api_secret,
            recv_window=20000 
        )
        if self.endpoint_env == "demo":
            self.session.endpoint = self.http_url

        print(f"[{self.symbol}] Client initialized for {self.category.upper()} on {self.endpoint_env.upper()}")
        self.precision_data = self._fetch_symbol_info()

    # ==================================================================
    # HELPER: PRECISION & ROUNDING (Internal)
    # ==================================================================
    @auto_resync()
    def _fetch_symbol_info(self):
        """Fetches precision data based on category."""
        response = self.session.get_instruments_info(
            category=self.category,
            symbol=self.symbol
        )
        info = response['result']['list'][0]
        
        # Spot and Linear have different field names for precision
        if self.category == "spot":
            return {
                'price_tick': str(info['priceFilter']['tickSize']),
                'qty_step': str(info['lotSizeFilter']['basePrecision']), # Spot specific field
                'min_qty': str(info['lotSizeFilter']['minOrderQty'])
            }
        return {
            'price_tick': str(info['priceFilter']['tickSize']),
            'qty_step': str(info['lotSizeFilter']['qtyStep']), # Linear specific field
            'min_qty': str(info['lotSizeFilter']['minOrderQty'])
        }
    def _round_qty(self, qty: float) -> str:
        """Rounds quantity DOWN to the nearest step size."""
        step = Decimal(self.precision_data['qty_step'])
        qty_dec = Decimal(str(qty))
        
        # Round down to nearest step
        rounded = (qty_dec // step) * step
        
        # Ensure minimum order quantity
        min_qty = Decimal(self.precision_data['min_qty'])
        if rounded < min_qty:
            return str(min_qty) 
            
        return f"{rounded:f}"

    def _round_price(self, price: float, side: str) -> str:
        """
        Rounds price safely based on order side.
        Buy -> Floor, Sell -> Ceiling.
        """
        tick = Decimal(self.precision_data['price_tick'])
        price_dec = Decimal(str(price))

        if side.lower() == "buy":
            rounded = price_dec.quantize(tick, rounding=ROUND_FLOOR)
        else:
            rounded = price_dec.quantize(tick, rounding=ROUND_CEILING)

        return f"{rounded:f}"

    # ==================================================================
    # ACCOUNT & MARKET DATA
    # ==================================================================
    @auto_resync()
    def get_usdt_balance(self) -> float:
        """Returns available USDT balance in the Unified account."""
        response = self.session.get_wallet_balance(
            accountType="UNIFIED",
            coin="USDT"
        )
        try:
            return float(response["result"]["list"][0]["coin"][0]["walletBalance"])
        except (IndexError, KeyError):
            return 0.0

    def get_current_price(self) -> float:
        """Gets the last traded price for the bound symbol."""
        response = self.session.get_tickers(
            category=self.category,  
            symbol=self.symbol
        )
        return float(response["result"]["list"][0]["lastPrice"])

    def get_open_position(self):
        """
        Returns position data for the current symbol.
        - For SPOT: Checks if the base coin balance exists in the wallet.
        - For LINEAR: Checks the active perpetual contract position.
        """
        if self.category == "spot":
            # Extract the coin name (e.g., 'XAUT' from 'XAUTUSDT')
            coin = self.symbol.replace("USDT", "")
            
            response = self.session.get_wallet_balance(
                accountType="UNIFIED",
                coin=coin
            )
            
            try:
                # Access the specific coin's data in the Unified account
                coin_list = response["result"]["list"][0]["coin"]
                if not coin_list:
                    return None
                    
                coin_data = coin_list[0]
                balance = float(coin_data["walletBalance"])
                
                # We consider a balance > 0.0001 as an active 'Buy' position
                # This prevents 'dust' amounts from triggering a Sell logic
                if balance > 0.0001: 
                    return {
                        "size": balance,
                        "qty": balance,
                        "side": "Buy",
                        "entry_price": 0.0  # Bybit Spot doesn't return entry_price via API
                    }
            except (IndexError, KeyError):
                return None
            return None

        # Logic for Linear Futures (Category: linear)
        response = self.session.get_positions(
            category="linear",
            symbol=self.symbol
        )
        
        data = response["result"]["list"]
        if not data:
            return None

        pos = data[0]
        if float(pos["size"]) > 0:
            return {
                "size": float(pos["size"]),
                "qty": float(pos["size"]),
                "side": pos["side"],
                "entry_price": float(pos["avgPrice"]),
                "unrealized_pnl": float(pos["unrealisedPnl"]),
                "leverage": pos["leverage"]
            }
        return None

    def get_candles(self, interval: str, limit: int = 200):
        """
        Fetches historical klines.
        :param interval: "1", "5", "15", "60", "D"
        :return: List of dicts [Oldest -> Newest]
        """
        response = self.session.get_kline(
            category=self.category, 
            symbol=self.symbol,
            interval=interval,
            limit=limit
        )
        
        raw_list = response["result"]["list"]
        raw_list.reverse() 
        
        cleaned_data = []
        for candle in raw_list:
            cleaned_data.append({
                "start_time": int(candle[0]),
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            })
            
        return cleaned_data

    def get_open_orders(self):
        """Fetches active Limit/Stop orders for the bound symbol."""
        response = self.session.get_open_orders(
            category="linear",
            symbol=self.symbol
        )
        
        orders = []
        if "list" in response["result"]:
            for order in response["result"]["list"]:
                orders.append({
                    "order_id": order["orderId"],
                    "price": float(order["price"]),
                    "qty": float(order["qty"]),
                    "side": order["side"],
                    "type": order["orderType"],
                    "status": order["orderStatus"]
                })
        return orders

    # ==================================================================
    # SETUP & EXECUTION
    # ==================================================================

    def setup_bot(self, leverage: int):
        """Switches to Isolated Margin and sets Leverage."""
        # Switch to Isolated
        try:
            self.session.switch_margin_mode(
                category="linear",
                symbol=self.symbol,
                tradeMode=1, # 1 = Isolated
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            # print(f"[{self.symbol}] Switched to Isolated Margin.")
        except InvalidRequestError as e:
            if "110026" not in str(e): 
                # print(f"Warning cant set margin mode: {e}")
                pass

        # Set Leverage
        try:
            self.session.set_leverage(
                category="linear",
                symbol=self.symbol,
                buyLeverage=str(leverage),
                sellLeverage=str(leverage)
            )
            # print(f"[{self.symbol}] Leverage set to {leverage}x.")
        except InvalidRequestError as e:
            if "110043" not in str(e):
                print(f"Warning setting leverage: {e}")

    def place_limit_order(self, side: str, qty: float, price: float, reduce_only: bool = False, post_only: bool = False) -> str:
        """
        Places a Limit order.
        :param post_only: If True, sets timeInForce to 'PostOnly' (guarantees Maker fee).
        Returns the Order ID (str).
        """
        safe_qty = self._round_qty(qty)
        safe_price = self._round_price(price, side)
        
        # Determine TimeInForce
        tif = "PostOnly" if post_only else "GTC"

        # print(f"[{self.symbol}] Placing LIMIT {side} ({tif}): {safe_qty} @ {safe_price}")

        response = self.session.place_order(
            category="linear",
            symbol=self.symbol,
            side=side.capitalize(),
            orderType="Limit",
            qty=safe_qty,
            price=safe_price,
            timeInForce=tif, 
            reduceOnly=reduce_only
        )
        return response['result']['orderId']

    @auto_resync()
    def place_market_order(self, side: str, qty: float, reduce_only: bool = False) -> str:
        safe_qty = self._round_qty(qty)
        response = self.session.place_order(
            category=self.category,  
            symbol=self.symbol,
            side=side.capitalize(),
            orderType="Market",
            qty=safe_qty,
            reduceOnly=reduce_only
        )
        print(f"DEBUG: Bybit Response -> {response}")
        return response['result']['orderId']

    def cancel_all_orders(self):
        return self.session.cancel_all_orders(
            category="linear",
            symbol=self.symbol
        )

    def get_order_history(self, limit: int = 50, start_time: int = None):
        """
        Fetches historical orders (Filled, Cancelled, Rejected).
        Bybit V5 Default: Last 7 days unless start_time is provided.
        
        :param limit: Number of records to fetch (max 100).
        :param start_time: (Optional) Start timestamp in milliseconds.
        """
        # Prepare arguments
        params = {
            "category": "linear",
            "symbol": self.symbol,
            "limit": limit
        }
        if start_time:
            params["startTime"] = start_time

        response = self.session.get_order_history(**params)
        
        history = []
        if "list" in response["result"]:
            for order in response["result"]["list"]:
                history.append({
                    "order_id": order["orderId"],
                    "price": float(order["price"]) if order["price"] else 0.0,
                    "avg_price": float(order["avgPrice"]) if order["avgPrice"] else 0.0, # Actual execution price
                    "qty": float(order["qty"]),
                    "filled_qty": float(order["cumExecQty"]), # Amount actually filled
                    "side": order["side"],
                    "type": order["orderType"],
                    "status": order["orderStatus"], # e.g., 'Filled', 'Cancelled'
                    "reduce_only": order["reduceOnly"],
                    "created_time": int(order["createdTime"]),
                    "updated_time": int(order["updatedTime"])
                })
        return history
    
    def get_historical_klines(self, interval: str, start_time_ms: int, end_time_ms: int = None):
        """Fetches historical candles with pagination support."""
        all_candles = []
        current_end = end_time_ms if end_time_ms else int(time.time() * 1000)
        
        while True:
            response = self.session.get_kline(
                category=self.category,
                symbol=self.symbol,
                interval=interval,
                end=current_end,
                limit=1000 
            )
            raw_list = response.get("result", {}).get("list", [])
            if not raw_list:
                break
            all_candles.extend(raw_list)
            oldest_candle_time = int(raw_list[-1][0])
            if oldest_candle_time <= start_time_ms:
                break
            current_end = oldest_candle_time - 1
            time.sleep(0.1)

        # Cleanup and convert to DataFrame
        df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit='ms')
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df.sort_values("timestamp").reset_index(drop=True)
    def start_kline_stream(self, callback, interval: str = "1"):
        """
        Starts a WebSocket stream for real-time klines.
        :param callback: A function to handle the incoming data.
        """
        ws = WebSocket(
            testnet=self.testnet,
            channel_type="linear",
            api_key=self.api_key,
            api_secret=self.api_secret,
        )

        def handle_message(msg):
            data = msg.get("data", [])
            if not data: return
            
            # Format to match our DataFrame structure
            candle = data[0]
            formatted_data = {
                "timestamp": pd.to_datetime(int(candle["start"]), unit='ms'),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
                "volume": float(candle["volume"])
            }
            callback(formatted_data)

        ws.kline_stream(
            interval=interval,
            symbol=self.symbol,
            callback=handle_message
        )

    def is_connected(self):
        try:
            self.session.get_server_time()
            return True
        except Exception:
            return False