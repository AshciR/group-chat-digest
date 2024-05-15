import asyncio
import logging

from server import run_server_async
from telegram_bot import get_application, run_bot_async

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

    asyncio.run(main())
