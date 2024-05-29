import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telegram import Update
from telegram.error import Forbidden
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler
from telegram.ext._application import Application, BaseHandler

from message_storage import (Message,
                             get_redis_client,
                             store_message,
                             chat_exists,
                             get_latest_n_messages,
                             DEFAULT_MESSAGE_STORAGE, configure_message_storage)
from openai_utils import get_ai_client, summarize_messages_as_bullet_points, summarize_messages_as_paragraph
from white_list import is_whitelisted

logger = logging.getLogger(__name__)

START_COMMAND = 'start'
SUMMARY_COMMAND = 'summary'
GIST_COMMAND = 'gist'
WHISPER_COMMAND = 'whspr'
HELP_COMMAND = 'help'


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Introduction command
    @param update:
    @param context:
    @return:
    """
    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        await context.bot.send_message(chat_id=chat_id, text="You are not currently allowed to use this bot")
        return

    start_msg = """Welcome to the ChatNuff bot 🗣️🤖!
    
I'm here to help you get caught up on what you missed in the group chat.

Use the /help command to learn about what I can do.
"""

    await context.bot.send_message(chat_id=chat_id, text=start_msg)


async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that summarizes the last N messages as paragraphs
    @param update:
    @param context:
    @return:
    """
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

        # Making assumption that the 1st argument is the number
        number_of_messages_to_summarize = await _determine_number_of_messages_from_message_context(context)

        messages = get_latest_n_messages(redis_client, chat_id, number_of_messages_to_summarize)
        # We have to reverse the list b/c Redis stores the latest message in index 0
        messages.reverse()

        # Send N messages to OpenAI
        prompt_message_schema = await format_message_for_openai(messages)
        summarized_msg = _summarize_messages_as_paragraph(prompt_message_schema)
        await context.bot.send_message(chat_id=chat_id, text=summarized_msg)


def _summarize_messages_as_paragraph(formatted_messages: str) -> str:

    client = get_ai_client()
    summary = summarize_messages_as_paragraph(client, formatted_messages)
    logger.debug(summary)

    return summary


async def whisper_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that summarizes the last N messages as bullet points
    and messages the user privately.
    @param update:
    @param context:
    @return:
    """

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

        # Making assumption that the 1st argument is the number
        number_of_messages_to_summarize = await _determine_number_of_messages_from_message_context(context)

        messages = get_latest_n_messages(redis_client, chat_id, number_of_messages_to_summarize)
        # We have to reverse the list b/c Redis stores the latest message in index 0
        messages.reverse()

        # Send N messages to OpenAI
        prompt_message_schema = await format_message_for_openai(messages)
        summarized_msg = _summarize_messages_as_bullet_points(prompt_message_schema)

        gist_prefix = f"Gist from {update.effective_chat.effective_name} chat:\n"
        private_gist = gist_prefix + summarized_msg

        # Send private message to the user
        try:
            await context.bot.send_message(chat_id=update.effective_user.id, text=private_gist)
        except Forbidden:
            warning_msg = "Sorry, but I can't message you privately unless you start a chat with me first."
            await context.bot.send_message(chat_id=chat_id, text=warning_msg)


async def gist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that summarizes the last N messages as bullet points
    @param update:
    @param context:
    @return:
    """

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

        # Making assumption that the 1st argument is the number
        number_of_messages_to_summarize = await _determine_number_of_messages_from_message_context(context)

        messages = get_latest_n_messages(redis_client, chat_id, number_of_messages_to_summarize)
        # We have to reverse the list b/c Redis stores the latest message in index 0
        messages.reverse()

        # Send N messages to OpenAI
        prompt_message_schema = await format_message_for_openai(messages)
        summarized_msg = _summarize_messages_as_bullet_points(prompt_message_schema)
        await context.bot.send_message(chat_id=chat_id, text=summarized_msg)


async def _determine_number_of_messages_from_message_context(context):
    if context.args and context.args[0].isdigit():
        number_of_messages = int(context.args[0])
    else:
        number_of_messages = DEFAULT_MESSAGE_STORAGE

    return number_of_messages


async def format_message_for_openai(messages: list[Message]) -> str:
    messages_content = [f"{msg.owner_name}: {msg.content}" for msg in messages]
    prompt_message_schema = ';'.join(messages_content)
    return prompt_message_schema


def _summarize_messages_as_bullet_points(formatted_messages: str) -> str:

    client = get_ai_client()
    summary = summarize_messages_as_bullet_points(client, formatted_messages)
    logger.debug(summary)

    return summary


async def _replay_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that replays the messages in storage
    Used for debugging purposes. DO NOT USE IN PRODUCTION!
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


async def listen_for_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    logger.debug(f'Got message: {message} from chat id: {chat_id}')

    redis_client = get_redis_client()
    count = store_message(redis_client, chat_id, message)
    logger.debug(f'Cache size: {count} from chat id: {chat_id}')


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that summarizes the last N messages as paragraphs
    @param update:
    @param context:
    @return:
    """
    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        await context.bot.send_message(chat_id=chat_id, text="You are not currently allowed to use this bot")
        return

    help_text = f"""Welcome to the ChatNuff bot 🗣️🤖!

Available commands:
/{SUMMARY_COMMAND} Summarizes the last {DEFAULT_MESSAGE_STORAGE} messages.
/{GIST_COMMAND} Gives you a bullet form of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{WHISPER_COMMAND} Privately messages you the bullet points of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{HELP_COMMAND}: Gives information about the bot.

The bot can also summarize a certain number of messages if you provide it with a number.

For example: /gist 50

Will give you the bullet form of the last 50 messages.
"""
    await context.bot.send_message(chat_id=chat_id, text=help_text)


def get_application():
    load_dotenv()

    if not configure_message_storage():
        logger.critical("Failed to configure the message storage. Exiting the application.")
        sys.exit(1)  # Exit the program with an error code

    telegram_token = os.getenv('TELEGRAM_API_KEY')

    application = ApplicationBuilder() \
        .token(telegram_token) \
        .build()

    handlers = get_handlers()

    for handler in handlers:
        application.add_handler(handler)

    return application


def get_handlers() -> list[BaseHandler]:
    return [
        CommandHandler(START_COMMAND, start_handler),
        CommandHandler(GIST_COMMAND, gist_handler),
        CommandHandler(SUMMARY_COMMAND, summary_handler),
        CommandHandler(HELP_COMMAND, help_handler),
        CommandHandler(WHISPER_COMMAND, whisper_handler),
        MessageHandler(filters.TEXT & (~filters.COMMAND), listen_for_messages_handler)
    ]


async def run_bot_async(application: Application):
    """
    Runs the bot asynchronously.
    Manually handles what :meth run_polling does.
    We need to do this to run a webserver concurrently with the bot.
    @param application:
    @return:
    """

    await application.initialize()

    updater = application.updater
    await updater.start_polling()

    await application.start()

    # Keep the event loop running
    try:
        while True:
            await asyncio.sleep(3600)  # Sleep for 1 hour and then re-check
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await updater.stop()
        await application.stop()
        await application.shutdown()
