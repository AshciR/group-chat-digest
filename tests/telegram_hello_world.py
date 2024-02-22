import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


def get_last_n_group_messages():
    # TODO: Figure out how to use Telegram bot to grab group messages
    return [""]


def summerize_messages(messages):
    # TODO: Figure out how to use OpenAI API
    return "Mock summarized message!"


async def summize(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Read last N messages of the group
    messages = get_last_n_group_messages()

    # Send N messages to OpenAI
    summarized_msg = summerize_messages(messages)

    # Send the result as a message
    await context.bot.send_message(chat_id=update.effective_chat.id, text=summarized_msg)


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_API_KEY')
    application = ApplicationBuilder().token(token).build()

    start_handler = CommandHandler('start', start)
    summize_handler = CommandHandler('summize', summize)

    application.add_handler(start_handler)
    application.add_handler(summize_handler)

    application.run_polling()
