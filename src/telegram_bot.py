import logging
import os
from collections import deque

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler

load_dotenv()

DEFAULT_MESSAGE_STORAGE = 5

# We're using a dictionary to store the chats id as the key,
# and the messages in a queue as the value for the time being.
message_storage = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the ChatNuff bot 🤖")


async def summarize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that summarizes the last N messages
    @param update:
    @param context:
    @return:
    """
    # Making assumption that the 1st argument is the number
    number_of_messages = await determine_number_of_messages(context)

    if update.effective_chat.id not in message_storage:
        empty_message_notice = "There are no messages to summarize"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=empty_message_notice)
    else:
        message_storage_queue = message_storage[update.effective_chat.id]
        messages = get_last_n_group_messages(number_of_messages, message_storage_queue)

        # Send N messages to OpenAI
        summarized_msg = summarize_messages(messages)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=summarized_msg)


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
    if update.effective_chat.id not in message_storage:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="There are no message to replay")

    else:
        message_storage_queue = message_storage[update.effective_chat.id]
        logging.debug(f'Replaying for chat id {update.effective_chat.id} currently in storage.')

        for message in message_storage_queue:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)


async def listen_for_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    # Command that listens for messages and stores them.
    @rtype: object
    """
    logging.info(f'Got message: {update.message.text} from chat id: {update.effective_chat.id}')
    _store_messages(update.message.text, update.effective_chat.id)


def _store_messages(message: str, chat_id: int):
    if chat_id not in message_storage:
        message_storage[chat_id] = deque([], DEFAULT_MESSAGE_STORAGE)

    message_queue = message_storage[chat_id]
    logging.debug(f"Storing message {message} from chat id: {chat_id}")
    message_queue.append(message)

    return len(message_queue)


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
