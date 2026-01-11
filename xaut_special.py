from client import Client
from manager import TradeManager




# Initialize Client
client = Client("XAUTUSDT")
client.setup_bot(leverage=5)

manager = TradeManager(client, maker_offset_buy=1, maker_offset_sell=1)

# manager.add_trade(target_entry=0.7273, target_exit=0.7279, qty=8,loop_trade=True)



# manager.load_from_disk("./results/linear.data")
manager.create_normal_traders(4401, 4553, 17, 0.002, 0.30, loop_trade=True, sigma_factor=4.0)


# low: 4401 -2.38%
# high: 4553 +1%

# true mean: 4170   -7.5%
# my mean: 4360    -3.3%

# Simulation Loop
import time
import signal
while True:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    manager.process_tick()
    manager.save_to_disk("./results/xaut.data")
    signal.signal(signal.SIGINT, signal.default_int_handler)
    time.sleep(5) # Rate limit protection
        
