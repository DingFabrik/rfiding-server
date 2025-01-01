import aioesphomeapi
from aioesphomeapi.reconnect_logic import ReconnectLogic
import asyncio

async def main():
    """Connect to an ESPHome device and wait for state changes."""
    cli = aioesphomeapi.APIClient("192.168.180.30", 6053, "")

    def change_callback(state):
        """Print the state changes of the device.."""
        print(state)

    def on_connect():
        print("Connected!")
        cli.subscribe_states(change_callback)
        cli.light_command(441677182, state=True, rgb=[1.0, 1.0, 0])
    
    reconnect_logic = ReconnectLogic(client=cli,
                                     on_connect=on_connect,
                                        on_disconnect=lambda: print("Disconnected!"))
    await reconnect_logic.start()

loop = asyncio.get_event_loop()
try:
    asyncio.ensure_future(main())
    loop.run_forever()
except KeyboardInterrupt:
    pass
finally:
    loop.close()