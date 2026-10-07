import asyncio
import logging
import signal

from django.core.management.base import BaseCommand

from machines.esphome.manager import DeviceManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Keeps native API connections to all machines with an encryption key open "
        "and relays commands and state between them and the website."
    )

    def handle(self, *args, **kwargs):
        asyncio.run(self.run())

    async def run(self):
        task = asyncio.current_task()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, task.cancel)
        try:
            await DeviceManager().run()
        except asyncio.CancelledError:
            logger.info("Machine manager stopped")
