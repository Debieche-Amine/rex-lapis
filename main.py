from client import Client

if __name__ == "__main__":
    # Initialize client specifically for BTC
    client = Client("BTCUSDT")



    # 1. Setup (Run once)
    client.setup_bot(leverage=5)

    # 2. Get Data
    price = client.get_current_price()
    print(f"Price: {price}")
    

    id = client.place_limit_order(side="Buy",qty=0.01,price=83266.00,post_only=True)
    print(id)


    orders = client.get_open_orders()

    print(f"Open Orders: {len(orders)}")
    print(orders)

    # 3. Trade (No need to pass "BTCUSDT" anymore)
    # client.place_market_order("Buy", 0.001)
