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
from telegram.constants import MessageEntityType

from models import Message
from message_storage import (get_redis_client,
                             store_message,
                             chat_exists,
                             get_latest_n_messages,
                             DEFAULT_MESSAGE_STORAGE, configure_message_storage, MAX_MESSAGE_STORAGE,
                             get_all_chat_ids, get_commands_analytics, update_command_analytics)
from openai_utils import get_ai_client, summarize_messages_as_bullet_points, summarize_messages_as_paragraph, \
    ping_openai, LLM_MODEL, convert_to_speech
from utils import remove_voice_message
from white_list import is_whitelisted, is_admin, get_admin_user_list

logger = logging.getLogger(__name__)

# Regular commands
START_COMMAND = 'start'
SUMMARY_COMMAND = 'summary'
GIST_COMMAND = 'gist'
WHISPER_GIST_COMMAND = 'whspr'
WHISPER_COMMAND = 'whisper'
HELP_COMMAND = 'help'
PRIVACY_COMMAND = 'privacy'

# Admin commands
REPLAY_COMMAND = 'replay'
STATUS_COMMAND = 'status'
BROADCAST_COMMAND = 'alert'
ANALYTICS_COMMAND = 'analytics'

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
        return

    # Making assumption that the 1st argument is the number
    number_of_messages_to_summarize = await _determine_number_of_messages_from_message_context(context)

    messages = get_latest_n_messages(redis_client, chat_id, number_of_messages_to_summarize)
    # We have to reverse the list b/c Redis stores the latest message in index 0
    messages.reverse()

    # Send N messages to OpenAI
    prompt_message_schema = await format_message_for_openai(messages)
    summarized_msg = _summarize_messages_as_paragraph(prompt_message_schema)

    send_as_voice_message = await does_user_want_a_voice_message(context)
    if send_as_voice_message:
        client = get_ai_client()

        path_to_voice_msg = convert_to_speech(client, summarized_msg)
        logger.debug(f"Summary voice message was created at {path_to_voice_msg}")

        await context.bot.send_voice(chat_id=chat_id, voice=path_to_voice_msg)
        remove_voice_message(path_to_voice_msg)
        await update_command_analytics(redis_client, f"{SUMMARY_COMMAND}-voice")
        return

    await context.bot.send_message(chat_id=chat_id, text=summarized_msg)
    await update_command_analytics(redis_client, SUMMARY_COMMAND)
    return


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

    await update_command_analytics(redis_client, WHISPER_GIST_COMMAND)
    return


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
        return

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

        send_as_voice_message = await does_user_want_a_voice_message(context)
        if send_as_voice_message:
            client = get_ai_client()

            path_to_voice_msg = convert_to_speech(client, private_summary)
            logger.debug(f"Whisper voice message was created at {path_to_voice_msg}")

            await context.bot.send_voice(chat_id=update.effective_user.id, voice=path_to_voice_msg)
            remove_voice_message(path_to_voice_msg)
            await update_command_analytics(redis_client, f"{WHISPER_COMMAND}-voice")
            return

        await context.bot.send_message(chat_id=update.effective_user.id, text=private_summary)
        await update_command_analytics(redis_client, WHISPER_COMMAND)
        return

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

    await update_command_analytics(redis_client, GIST_COMMAND)
    return


async def _determine_number_of_messages_from_message_context(context):
    if context.args and context.args[0].isdigit():
        number_of_messages = int(context.args[0])
    else:
        number_of_messages = DEFAULT_MESSAGE_STORAGE

    return number_of_messages


async def does_user_want_a_voice_message(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Determines if the second argument in the message context is 'voice'.

    Args:
        context: The message context containing arguments (context.args).

    Returns:
        bool: True if the second argument is 'voice', False otherwise.
    """
    return any(arg.lower() == "voice" for arg in context.args[:2])


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

    # We're not storing messages that contain spoilers in them
    if does_message_contain_spoilers(update.message):
        logger.debug(f"Message id {update.message.id} contained a spoiler. Not storing it")
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


def does_message_contain_spoilers(message) -> bool:
    has_entity = any(entity.type == MessageEntityType.SPOILER for entity in message.entities)
    return has_entity


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that shows how to use the bot
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
/{SUMMARY_COMMAND} : Summarizes the last {DEFAULT_MESSAGE_STORAGE} messages.
/{SUMMARY_COMMAND} voice : Summarizes the last {DEFAULT_MESSAGE_STORAGE} messages as a voice message.
/{GIST_COMMAND} : Gives you a bullet form of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{WHISPER_COMMAND} voice : Privately voice messages you the summary of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{WHISPER_GIST_COMMAND} : Privately messages you the bullet points of the last {DEFAULT_MESSAGE_STORAGE} messages.
/{HELP_COMMAND} : Gives usage information about the bot.
/{PRIVACY_COMMAND} : Gives privacy information about the bot.

I can also summarize a certain number of messages if you provide me with a number.

For example: /gist 50

Will give you the bullet form of the last 50 messages.

However, the maximum number of messages I can handle is {MAX_MESSAGE_STORAGE}.

Happy chatting! 🗣️❤️

Bot Artwork created by [@Spritewrench](https://spritewrench.com/) 🎨

"""
    await context.bot.send_message(chat_id=chat_id, text=help_text, parse_mode="markdown")

    redis_client = get_redis_client()
    await update_command_analytics(redis_client, HELP_COMMAND)
    return


async def privacy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that shows the privacy info
    @param update:
    @param context:
    @return:
    """
    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        await context.bot.send_message(chat_id=chat_id, text=NOT_WHITE_LISTED_FRIENDLY_MESSAGE)
        return

    privacy_policy = (
        "**Privacy Policy for ChatNuffBot**\n\n"
        "**Effective Date:** Dec 31, 2024\n\n"
        "@ChatNuffBot (\"the Bot\") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you interact with the Bot.\n\n"
        "**1. Information We Collect**\n"
        "- **Messages**: The last 200 messages from group chats, including their metadata.\n"
        "- **Metadata about Messages**:\n"
        "  - `message_id`: A unique identifier for the message.\n"
        "  - `content`: The text content of the message.\n"
        "  - `owner_id`: The unique ID of the user who sent the message.\n"
        "  - `owner_name`: The username or display name of the message sender.\n"
        "  - `created_at`: The timestamp of when the message was sent.\n"
        "- **Bot Command Usage**: Logs of commands issued to the Bot for analytics purposes.\n\n"
        "**2. How We Use Your Information**\n"
        "- To provide, maintain, and improve the Bot’s functionality, such as summarizing user messages.\n"
        "- To analyze bot command usage for identifying and enhancing user value.\n\n"
        "**3. Data Sharing and Disclosure**\n"
        "- We do not sell, trade, or share your information with any third parties.\n\n"
        "**4. Data Retention**\n"
        "- Only the last 200 messages for a chat are retained at any point in time. This data is encrypted during transit and at rest.\n\n"
        "**5. Your Rights**\n"
        "- Access to, correction of, or deletion of collected message data is not provided.\n\n"
        "**6. Data Security**\n"
        "- Data is encrypted during transit and at rest to prevent unauthorized access.\n\n"
        "**7. Third-Party Services**\n"
        "- The Bot operates within the Telegram platform, which has its own privacy policy.\n\n"
        "**8. Changes to This Privacy Policy**\n"
        "- We may update this Privacy Policy from time to time. Please review it periodically.\n\n"
        "**9. Contact Us**\n"
        "If you have questions or concerns about this Privacy Policy, contact us at @Ashcir.\n"
    )

    await context.bot.send_message(chat_id=chat_id, text=privacy_policy, parse_mode="markdown")

    redis_client = get_redis_client()
    await update_command_analytics(redis_client, PRIVACY_COMMAND)
    return


#####################################################################
# The following handlers are only for development and admin purposes!
#####################################################################
async def replay_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that replays the messages in storage
    Used for debugging purposes.
    @rtype: object
    """

    if not await _is_admin_user(update, context):
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

    if not await _is_admin_user(update, context):
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


async def analytics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Reports the analytics of the bot usage.
    Examples are: command usage, number of chats stores, etc.
    NOTE: Should only be used by Admins
    @param update:
    @param context:
    @return:
    """

    if not await _is_admin_user(update, context):
        return

    # Get the analytics for command usage. Can implement more later
    redis = get_redis_client()
    command_analytics = await get_commands_analytics(redis)

    # Send message to all the chats
    analytics_msg = "Command usage:\n" + "".join(
        f"{command}: {count}  \n"
        for command, count in command_analytics.items()
    )

    await update.message.reply_text(analytics_msg)
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
Model: {LLM_MODEL}
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
        CommandHandler(PRIVACY_COMMAND, privacy_handler),
        MessageHandler(filters.TEXT & (~filters.COMMAND), listen_for_messages_handler)
    ]


def get_admin_handlers() -> list[BaseHandler]:
    return [
        CommandHandler(REPLAY_COMMAND, replay_messages_handler),
        CommandHandler(STATUS_COMMAND, status_handler),
        CommandHandler(BROADCAST_COMMAND, broadcast_handler),
        CommandHandler(ANALYTICS_COMMAND, analytics_handler),
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
