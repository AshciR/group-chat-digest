import asyncio
import logging
import os

from server import run_server_async
from telegram_bot import get_application, run_bot_async
from utils import str_to_bool

logger = logging.getLogger(__name__)


async def main():
    application = get_application()
    logger.info("Built the chat-nuff application")

    bot_task = run_bot_async(application)
    logger.info("Running the chat-nuff application")

    server_task = run_server_async()
    logger.info("Started the webserver")

    await asyncio.gather(bot_task, server_task)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    debug_mode = str_to_bool(os.getenv('DEBUG', False))

    if debug_mode:
        logging.getLogger('telegram_bot').setLevel(logging.DEBUG)
        logging.getLogger('message_storage').setLevel(logging.DEBUG)

    asyncio.run(main())
