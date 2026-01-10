import os
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
from pybit.exceptions import InvalidRequestError

# Load environment variables
load_dotenv()

class Client:
    def __init__(self, symbol: str):
        """
        Initializes the HTTP session and binds this client to a specific symbol.
        Forces 'linear' category (USDT Perpetuals).
        """
        self.api_key = os.getenv("API_KEY")
        self.api_secret = os.getenv("API_SECRET")
        self.testnet = os.getenv("API_TEST", "false").lower() == "true"
        
        self.symbol = symbol.upper()

        self.session = HTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )

        # Cache precision data immediately upon startup
        self.precision_data = self._fetch_symbol_info()
    

    # ==================================================================
    # HELPER: PRECISION & ROUNDING (Internal)
    # ==================================================================

    def _fetch_symbol_info(self):
        """Fetches tick size (price) and step size (qty) for the bound symbol."""
        response = self.session.get_instruments_info(
            category="linear",
            symbol=self.symbol
        )
        
        info = response['result']['list'][0]
        return {
            'price_tick': str(info['priceFilter']['tickSize']),
            'qty_step': str(info['lotSizeFilter']['qtyStep']),
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
            category="linear",
            symbol=self.symbol
        )
        return float(response["result"]["list"][0]["lastPrice"])

    def get_open_position(self):
        """
        Returns a dictionary of position data if it exists (size > 0).
        Otherwise returns None.
        """
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
            category="linear",
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
            print(f"[{self.symbol}] Switched to Isolated Margin.")
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
            print(f"[{self.symbol}] Leverage set to {leverage}x.")
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

        print(f"[{self.symbol}] Placing LIMIT {side} ({tif}): {safe_qty} @ {safe_price}")

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

    def place_market_order(self, side: str, qty: float, reduce_only: bool = False) -> str:
        """
        Places a Market order.
        Returns the Order ID (str).
        """
        safe_qty = self._round_qty(qty)

        print(f"[{self.symbol}] Placing MARKET {side}: {safe_qty}")

        response = self.session.place_order(
            category="linear",
            symbol=self.symbol,
            side=side.capitalize(),
            orderType="Market",
            qty=safe_qty,
            reduceOnly=reduce_only
        )
        return response['result']['orderId']

    def cancel_all_orders(self):
        return self.session.cancel_all_orders(
            category="linear",
            symbol=self.symbol
        )

