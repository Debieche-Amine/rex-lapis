from client import Client
from manager import TradeManager

# ==========================================
# Example Usage Mockup
# ==========================================


if __name__ == "__main__":
    # Initialize Client
    client = Client("ASTERUSDT")
    client.setup_bot(leverage=5)
    
    manager = TradeManager(client, maker_offset_buy=0.0001, maker_offset_sell=0.0001)
    
    # Add a trade plan
    manager.add_trade(target_entry=0.8372, target_exit=0.7363, qty=8,loop_trade=True)
    manager.add_trade(target_entry=0.8412, target_exit=0.7434, qty=7)
    
    # Simulation Loop
    import time
    while True:
        manager.process_tick()
        time.sleep(3) # Rate limit protection
            
