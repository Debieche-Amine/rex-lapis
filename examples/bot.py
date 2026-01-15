from RexLapisLib import TradeManager,Client




# Initialize Client
client = Client("ASTERUSDT")
client.setup_bot(leverage=5)

manager = TradeManager(client, maker_offset_buy=0.0001, maker_offset_sell=0.0003)

# manager.add_trade(target_entry=0.7273, target_exit=0.7279, qty=8,loop_trade=True)



manager.create_linear_traders(0.7194, 0.7284, 22, 8, 0.10, loop_trade=True )


# Simulation Loop
import time
while True:
    manager.process_tick()
    manager.save_to_disk("./results/linear.data")
    time.sleep(5) # Rate limit protection
        
