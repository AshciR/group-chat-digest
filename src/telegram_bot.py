import logging
import os
import sys
from typing import Sequence

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler

from message_storage import (Message,
                             get_redis_client,
                             store_message,
                             chat_exists,
                             get_latest_n_messages,
                             DEFAULT_MESSAGE_STORAGE, configure_message_storage)

from openai_utils import get_ai_client, summarize_messages_using_ai
from white_list import is_whitelisted

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        await context.bot.send_message(chat_id=chat_id, text="You are not currently allowed to use this bot")
        return

    await context.bot.send_message(chat_id=chat_id, text="Welcome to the ChatNuff bot 🤖")


async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that summarizes the last N messages
    @param update:
    @param context:
    @return:
    """
    # Making assumption that the 1st argument is the number
    number_of_messages_to_summarize = await _determine_number_of_messages_from_message_context(context)

    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        await context.bot.send_message(chat_id=chat_id, text="You are not currently allowed to use this bot")
        return

    redis_client = get_redis_client()

    if not chat_exists(redis_client, chat_id):
        empty_message_notice = "There are no messages to summarize"
        await context.bot.send_message(chat_id=chat_id, text=empty_message_notice)
    else:

        messages = get_latest_n_messages(redis_client, chat_id, number_of_messages_to_summarize)
        # We have to reverse the list b/c Redis stores the latest message in index 0
        messages.reverse()

        # Send N messages to OpenAI
        summarized_msg = _summarize_messages(messages)
        await context.bot.send_message(chat_id=chat_id, text=summarized_msg)


async def _determine_number_of_messages_from_message_context(context):
    if context.args and context.args[0].isdigit():
        number_of_messages = int(context.args[0])
    else:
        number_of_messages = DEFAULT_MESSAGE_STORAGE

    return number_of_messages


def _summarize_messages(messages: Sequence[Message]) -> str:
    messages_content = [f"{msg.owner_name}: {msg.content}" for msg in messages]
    prompt_message_schema = ';'.join(messages_content)

    client = get_ai_client()
    summary = summarize_messages_using_ai(client, prompt_message_schema)
    logger.info(summary)

    return summary


async def replay_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    # Command that replays the messages in storage
    @rtype: object
    """

    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        await context.bot.send_message(chat_id=chat_id, text="You are not currently allowed to use this bot")
        return

    redis_client = get_redis_client()

    if not chat_exists(redis_client, chat_id):
        await context.bot.send_message(chat_id=chat_id, text="There are no message to replay")

    else:
        logger.debug(f'Replaying for chat id {chat_id} currently in storage.')

        messages = get_latest_n_messages(redis_client, chat_id)
        for message in messages[::-1]:
            await context.bot.send_message(chat_id=chat_id, text=message.content)


async def listen_for_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    # Command that listens for messages and stores them.
    @rtype: object
    """

    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        return



    message_owner = Message.convert_update_to_owner(update)
    message = Message(
        message_id=update.message.id,
        owner_id=update.message.from_user.id,
        content=update.message.text,
        owner_name=message_owner,
        created_at=update.message.date.isoformat()
    )
    logger.info(f'Got message: {message} from chat id: {chat_id}')

    redis_client = get_redis_client()
    count = store_message(redis_client, chat_id, message)
    logger.info(f'Cache size: {count} from chat id: {chat_id}')


if __name__ == '__main__':

    load_dotenv()

    if not configure_message_storage():
        logger.critical("Failed to configure the message storage. Exiting the application.")
        sys.exit(1)  # Exit the program with an error code

    telegram_token = os.getenv('TELEGRAM_API_KEY')

    application = ApplicationBuilder() \
        .token(telegram_token) \
        .build()

    handlers = [
        CommandHandler('start', start),
        CommandHandler('gist', summarize),
        CommandHandler('replay', replay_messages),
        MessageHandler(filters.TEXT & (~filters.COMMAND), listen_for_messages)
    ]

    for handler in handlers:
        application.add_handler(handler)

    application.run_polling()
