import logging
import os
from collections import deque

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler

load_dotenv()

DEFAULT_MESSAGE_STORAGE = 5
message_storage = deque([], DEFAULT_MESSAGE_STORAGE)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the ChatNuff bot 🤖")


async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Making assumption that the 1st argument is the number
    number_of_messages = await determine_number_of_messages(context)

    # Read last N messages of the group
    messages = get_last_n_group_messages(number_of_messages, message_storage)

    # Send N messages to OpenAI
    summarized_msg = summarize_messages(messages)

    if summarized_msg:
        # Send the result as a message
        await context.bot.send_message(chat_id=update.effective_chat.id, text=summarized_msg)
    else:
        empty_message_notice = "There are no messages to summarize"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=empty_message_notice)


async def determine_number_of_messages(context):
    if context.args and context.args[0].isdigit():
        number_of_messages = int(context.args[0])
    else:
        number_of_messages = DEFAULT_MESSAGE_STORAGE

    return number_of_messages


def get_last_n_group_messages(number_of_messages: int, message_queue=None):
    # Create a defensive copy as a good programming practice
    list_of_strings = list(message_queue)

    # Return the last n strings. If n is larger than the deque, return the whole list
    return list_of_strings[-number_of_messages:]


def summarize_messages(messages):
    # TODO: Figure out how to use OpenAI API
    summary = ','.join(messages)
    return summary


async def replay_messages_in_storage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    # Command that replays the messages in storage
    @rtype: object
    """
    logging.debug(f'Currently in storage: {message_storage}')
    for message in message_storage:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def listen_for_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    # Command that listens for messages and stores them.
    @rtype: object
    """
    logging.info(f'got message: {update.message.text}')
    _store_messages(update.message.text)


def _store_messages(message):
    message_storage.append(message)


if __name__ == '__main__':
    telegram_token = os.getenv('TELEGRAM_API_KEY')

    application = ApplicationBuilder() \
        .token(telegram_token) \
        .build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    summarize_handler = CommandHandler('gist', summarize)
    application.add_handler(summarize_handler)

    spit_handler = CommandHandler('replay', replay_messages_in_storage)
    application.add_handler(spit_handler)

    listen_for_messages_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), listen_for_messages)
    application.add_handler(listen_for_messages_handler)

    application.run_polling()
