import asyncio
import json
import logging
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.error import Forbidden, BadRequest
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler
from telegram.ext._application import Application, BaseHandler

from message_storage import (Message,
                             get_redis_client,
                             store_message,
                             chat_exists,
                             get_latest_n_messages,
                             DEFAULT_MESSAGE_STORAGE, configure_message_storage, MAX_MESSAGE_STORAGE,
                             get_all_chat_ids)
from openai_utils import get_ai_client, summarize_messages_as_bullet_points, summarize_messages_as_paragraph, \
    ping_openai, OPEN_AI_MODEL
from white_list import is_whitelisted, is_admin, get_admin_user_list

logger = logging.getLogger(__name__)

# Regular commands
START_COMMAND = 'start'
SUMMARY_COMMAND = 'summary'
GIST_COMMAND = 'gist'
WHISPER_GIST_COMMAND = 'whspr'
WHISPER_COMMAND = 'whisper'
HELP_COMMAND = 'help'

# Admin commands
REPLAY_COMMAND = 'replay'
STATUS_COMMAND = 'status'
BROADCAST_COMMAND = 'alert'

NOT_WHITE_LISTED_FRIENDLY_MESSAGE = (
    "Welcome to the ChatNuff bot 🗣️🤖!\n\n"
    "Currently, you don't have permission to give me commands in this chat. "
    "However, I can respond to you privately here if you use me in chats where I have the necessary permissions."
)


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
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
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
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
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


async def whisper_gist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
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

        gist_prefix = f"Gist from {update.effective_chat.effective_name} chat:\n\n"
        private_gist = gist_prefix + summarized_msg

        # Send private message to the user
        try:
            await context.bot.send_message(chat_id=update.effective_user.id, text=private_gist)
        except Forbidden:
            warning_msg = "Sorry, but I can't message you privately unless you start a chat with me first."
            await context.bot.send_message(chat_id=chat_id, text=warning_msg)


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
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
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

        summary_prefix = f"Summary from {update.effective_chat.effective_name} chat:\n\n"
        private_summary = summary_prefix + summarized_msg

        # Send private message to the user
        try:
            await context.bot.send_message(chat_id=update.effective_user.id, text=private_summary)
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
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
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

    # We want to add an extra line between the points for readability
    bullet_points = summary.strip().split('\n')
    formatted_bullet_points = '\n\n'.join(bullet_points)

    logger.debug(formatted_bullet_points)

    return formatted_bullet_points


async def listen_for_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    # Command that listens for messages and stores them.
    @rtype: object
    """

    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
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
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
        return

    help_text = f"""Welcome to the ChatNuff bot 🗣️🤖!

Available commands:
/{SUMMARY_COMMAND} Summarizes the last {DEFAULT_MESSAGE_STORAGE} messages.
/{GIST_COMMAND} Gives you a bullet form of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{WHISPER_COMMAND} Privately messages you the summary of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{WHISPER_GIST_COMMAND} Privately messages you the bullet points of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{HELP_COMMAND}: Gives information about the bot.

I can also summarize a certain number of messages if you provide me with a number.

For example: /gist 50

Will give you the bullet form of the last 50 messages.

However, the maximum number of messages I can handle is {MAX_MESSAGE_STORAGE}.

Happy chatting! 🗣️❤️

Bot Artwork created by [@Spritewrench](https://spritewrench.com/) 🎨

"""
    await context.bot.send_message(chat_id=chat_id, text=help_text, parse_mode="markdown")


#####################################################################
# The following handlers are only for development and admin purposes!
#####################################################################
async def replay_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that replays the messages in storage
    Used for debugging purposes.
    @rtype: object
    """

    if not _is_admin_user(update, context):
        return

    redis_client = get_redis_client()
    chat_id = update.effective_chat.id

    if not chat_exists(redis_client, chat_id):
        await context.bot.send_message(chat_id=chat_id, text="There are no message to replay")

    else:
        logger.info(f'Replaying for chat id {chat_id} currently in storage.')

        messages = get_latest_n_messages(redis_client, chat_id)
        for message in messages[::-1]:
            await context.bot.send_message(chat_id=chat_id, text=message.content)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that gets the status of the bot.
    Used for debugging purposes.
    @rtype: object
    """

    if not _is_admin_user(update, context):
        return

    chat_id = update.effective_chat.id

    # Open AI
    ai_client = get_ai_client()
    open_ai_status = await _get_open_ai_status(ai_client)
    logger.info(open_ai_status)

    # Redis
    redis = get_redis_client()
    redis_msg = await _get_redis_status(redis)
    logger.info(redis_msg)

    status_msg = f"""{open_ai_status} 
{redis_msg}
"""
    await context.bot.send_message(chat_id=chat_id, text=status_msg)


async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Alerts all groups that use the bot.
    Should be used judiciously to inform users,
    and not spam them with updates.
    @param update:
    @param context:
    @return:
    """

    if not await _is_admin_user(update, context):
        return

    if len(context.args) < 1:
        await update.message.reply_text("Broadcast message can not be empty")
        return

    # Find the chats the bot is in
    redis = get_redis_client()
    chat_ids: set[int] = get_all_chat_ids(redis)

    # Send message to all the chats
    broadcast_msg = update.effective_message.text.replace("/alert", "", 1).strip()
    logger.info(f"Broadcasting '{broadcast_msg}' to {len(chat_ids)} chats")
    for chat_id in chat_ids:
        try:
            logger.info(f"Sending broadcast message to chat id: {chat_id}")
            await context.bot.send_message(chat_id=chat_id, text=broadcast_msg, parse_mode="markdown")
        except BadRequest:
            logger.error(f"Failed to send broadcast message to chat id: {chat_id}. Status code: 400")
        except Forbidden:
            logger.error(f"Failed to send broadcast message to chat id: {chat_id}. Status code: 403")
        except Exception:
            logger.exception(f"Failed to send broadcast message to chat id: {chat_id}.")

    return


async def _is_admin_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_admin(user_id):
        logger.info(f'user id: {user_id} attempted to use the bot but was not an admin')
        await context.bot.send_message(chat_id=chat_id, text="You are not allowed to access this command")

        for admin_chat_id in get_admin_user_list():
            msg = f"User: {update.effective_user.full_name} attempted to use an admin command. Details user_id: {user_id} chat_id: {chat_id}"
            await context.bot.send_message(chat_id=admin_chat_id, text=msg)

        return False
    else:
        return True


async def _get_redis_status(redis) -> str:
    is_connected = redis.ping()
    connection_info = redis.client().connection
    redis_info = redis.info()
    keys_to_extract = ['redis_version', 'uptime_in_days', 'listener0', 'used_memory_human']
    condensed_redis_info = {
        key: redis_info[key]
        for key in keys_to_extract
        if key in redis_info
    }
    redis_msg = f"""Redis
Bot connected to Redis: {is_connected}
Redis connection: {connection_info}
Redis info: {json.dumps(condensed_redis_info, indent=4)}
    """
    return redis_msg


async def _get_open_ai_status(ai_client: OpenAI) -> str:
    open_ai_response = ping_openai(ai_client)
    open_ai_msg = f"""OpenAI 
Status: {open_ai_response}
Model: {OPEN_AI_MODEL}
    """
    return open_ai_msg


def get_application():
    load_dotenv()

    if not configure_message_storage():
        logger.critical("Failed to configure the message storage. Exiting the application.")
        sys.exit(1)  # Exit the program with an error code

    telegram_token = os.getenv('TELEGRAM_API_KEY')

    application = ApplicationBuilder() \
        .token(telegram_token) \
        .build()

    handlers = [
        *get_handlers(),
        *get_admin_handlers()
    ]

    for handler in handlers:
        application.add_handler(handler)

    return application


def get_handlers() -> list[BaseHandler]:
    return [
        CommandHandler(START_COMMAND, start_handler),
        CommandHandler(GIST_COMMAND, gist_handler),
        CommandHandler(SUMMARY_COMMAND, summary_handler),
        CommandHandler(HELP_COMMAND, help_handler),
        CommandHandler(WHISPER_GIST_COMMAND, whisper_gist_handler),
        CommandHandler(WHISPER_COMMAND, whisper_handler),
        MessageHandler(filters.TEXT & (~filters.COMMAND), listen_for_messages_handler)
    ]


def get_admin_handlers() -> list[BaseHandler]:
    return [
        CommandHandler(REPLAY_COMMAND, replay_messages_handler),
        CommandHandler(STATUS_COMMAND, status_handler),
        CommandHandler(BROADCAST_COMMAND, broadcast_handler),
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
