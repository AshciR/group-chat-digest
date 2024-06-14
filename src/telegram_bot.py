import asyncio
import json
import logging
import os
import re
import sys
from typing import Tuple

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, MessageEntity
from telegram.constants import MessageEntityType
from telegram.error import Forbidden
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler
from telegram.ext._application import Application, BaseHandler

from message_storage import (Message,
                             get_redis_client,
                             store_message,
                             chat_exists,
                             get_latest_n_messages,
                             DEFAULT_MESSAGE_STORAGE, configure_message_storage, MAX_MESSAGE_STORAGE, SpoilerRange)
from openai_utils import get_ai_client, summarize_messages_as_bullet_points, summarize_messages_as_paragraph, \
    ping_openai, summarize_messages_with_spoilers_as_paragraph, summarize_messages_with_spoilers_as_bullet_points
from white_list import is_whitelisted, is_admin, get_admin_user_list

logger = logging.getLogger(__name__)

# Regular commands
START_COMMAND = 'start'
SUMMARY_COMMAND = 'summary'
GIST_COMMAND = 'gist'
WHISPER_COMMAND = 'whspr'
HELP_COMMAND = 'help'

# Admin commands
REPLAY_COMMAND = 'replay'
STATUS_COMMAND = 'status'


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
        summarized_msg = await _summarize_messages_as_paragraph(messages)
        await context.bot.send_message(chat_id=chat_id, text=summarized_msg)


async def _summarize_messages_as_paragraph(messages: list[Message]) -> str:
    client = get_ai_client()

    formatted_messages = await format_message_for_openai(messages)
    has_spoilers = any(message.has_spoilers for message in messages)

    if has_spoilers:
        wrapped_summary = summarize_messages_with_spoilers_as_paragraph(client, formatted_messages)
        summary = unwrap_spoiler_content(wrapped_summary)
    else:
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
        summarized_msg = await _summarize_messages_as_bullet_points(messages)

        gist_prefix = f"Gist from {update.effective_chat.effective_name} chat:\n\n"
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
        summarized_msg = await _summarize_messages_as_bullet_points(messages)
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


async def _summarize_messages_as_bullet_points(messages: list[Message]) -> str:
    client = get_ai_client()

    formatted_messages = await format_message_for_openai(messages)
    has_spoilers = any(message.has_spoilers for message in messages)

    if has_spoilers:
        # The summary will have words surrounded by '^'.
        # We need to remove the '^' and generate spoiler ranges
        wrapped_summary = summarize_messages_with_spoilers_as_bullet_points(client, formatted_messages)
        summary = unwrap_spoiler_content(wrapped_summary)
    else:
        summary = summarize_messages_as_bullet_points(client, formatted_messages)

    # We want to add an extra line between the points for readability
    bullet_points = summary.strip().split('\n')
    formatted_bullet_points = '\n\n'.join(bullet_points)

    logger.debug(formatted_bullet_points)

    return formatted_bullet_points


def unwrap_spoiler_content(wrapped_summary: str) -> Tuple[str, list[SpoilerRange]]:
    """
    Unwraps spoiler content from a wrapped summary.

    @param wrapped_summary: The text with spoilers wrapped in '^'
    @return: A tuple containing the unwrapped text and a list of SpoilerRange objects
    """
    spoiler_ranges = []
    unwrapped_text = []
    current_index = 0

    # Regular expression to find text wrapped in '^'
    pattern = re.compile(r'\^(.*?)\^')

    for match in pattern.finditer(wrapped_summary):
        start, end = match.span()
        spoiler_content = match.group(1)

        # Add text before the spoiler
        unwrapped_text.append(wrapped_summary[current_index:start])

        # Calculate the start index and length of the spoiler content
        start_index = len(''.join(unwrapped_text))
        length = len(spoiler_content)

        # Append the spoiler content to the unwrapped text
        unwrapped_text.append(spoiler_content)

        # Add the spoiler range to the list
        spoiler_ranges.append(SpoilerRange(start_index=start_index, length=length))

        # Update the current index to the end of the current match
        current_index = end

    # Add any remaining text after the last spoiler
    unwrapped_text.append(wrapped_summary[current_index:])

    # Join all parts into the final unwrapped text
    final_text = ''.join(unwrapped_text)

    return final_text, spoiler_ranges


async def listen_for_messages_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    # Command that listens for messages and stores them.
    @rtype: object
    """

    chat_id = update.effective_chat.id

    if not is_whitelisted(chat_id):
        logger.info(f'chat id: {chat_id} attempted to use the bot but was not whitelisted')
        return

    message = create_message_from_update(update)
    logger.debug(f'Got message: {message} from chat id: {chat_id}')

    redis_client = get_redis_client()
    count = store_message(redis_client, chat_id, message)
    logger.debug(f'Cache size: {count} from chat id: {chat_id}')


def create_message_from_update(update: Update) -> Message:
    effective_message = update.effective_message

    # Check if the message has spoilers
    spoiler_entities: list[MessageEntity] = [
        entity
        for entity in effective_message.entities
        if entity.type == MessageEntityType.SPOILER
    ]
    has_spoiler = bool(spoiler_entities)

    if has_spoiler:
        start_indices_and_lengths = [SpoilerRange(entity.offset, entity.length) for entity in spoiler_entities]
        modified_content = modify_content_for_spoilers(effective_message.text, start_indices_and_lengths)

        return Message(
            message_id=update.message.id,
            owner_id=update.message.from_user.id,
            content=modified_content,
            owner_name=Message.convert_update_to_owner(update),
            created_at=update.message.date.isoformat(),
            has_spoilers=has_spoiler
        )

    # Return the unmodified message
    return Message(
        message_id=update.message.id,
        owner_id=update.message.from_user.id,
        content=update.message.text,
        owner_name=(Message.convert_update_to_owner(update)),
        created_at=update.message.date.isoformat(),
        has_spoilers=has_spoiler
    )


def modify_content_for_spoilers(text: str, start_indices_and_lengths: list[SpoilerRange]) -> str:
    """
    Converts the telegram message text into a format we use to display spoilers.
    Spoiler texts will be wrapped by the "^" symbol. E.g.
    "I am spoiler text" is converted to
    "I am ^spoiler^ text"

    Also note, that if the original text has "^" characters in it.
    They'll be replaced by "*". E.g.
    "I ^am spoiler text" is converted to
    "I *am spoiler text"

    @param text: the original text
    @param start_indices_and_lengths: a list of the start indexes and length of spoilt content
    @return: the modified text wrapped by "^"
    """
    # Replace the carrot symbol with '*' b/c we're using the carrot
    # to mark the start and end of spoiler content.
    # We chose the carrot symbol b/c the likelihood of a message container it was low.
    cleaned_message = text.replace("^", "*")

    # Wrap the spoiler content with ^
    wrapper_char = "^"
    modified_content = _wrap_spoiler_content(cleaned_message, start_indices_and_lengths, wrapper_char)

    return modified_content


def _wrap_spoiler_content(text: str, ranges: list[SpoilerRange], wrapper_char="^") -> str:
    # Sort ranges by starting index to avoid issues with overlapping ranges
    ranges = sorted(ranges, key=lambda x: x.start_index)

    # Initialize an empty list to hold the parts of the modified string
    modified_parts = []
    previous_end = 0

    # Iterate through the indices and lengths and wrap the specified words with "^"
    for range_ in ranges:
        end = range_.start_index + range_.length
        # Add the part of the string before the current word
        modified_parts.append(text[previous_end:range_.start_index])
        # Add the current word wrapped with "^"
        modified_parts.append(wrapper_char + text[range_.start_index:end] + wrapper_char)
        # Update the previous_end to the end of the current word
        previous_end = end

    # Add the remaining part of the string after the last word
    modified_parts.append(text[previous_end:])

    # Join all parts into the final modified string
    return ''.join(modified_parts)


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

I can also summarize a certain number of messages if you provide me with a number.

For example: /gist 50

Will give you the bullet form of the last 50 messages.

However, the maximum number of messages I can handle is {MAX_MESSAGE_STORAGE}.

Happy chatting! 🗣️❤️
"""
    await context.bot.send_message(chat_id=chat_id, text=help_text)


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

        # We're limiting the replay to 10 messages b/c Telegram has rate limiting in place
        # for the context.bot.send_message() function
        default_replay_arg = 10
        replay_arg = await _determine_number_of_messages_from_message_context(context)
        number_of_msg_to_replay = default_replay_arg if replay_arg == DEFAULT_MESSAGE_STORAGE else replay_arg

        messages = get_latest_n_messages(redis_client, chat_id, number_of_msg_to_replay)
        for message in messages[::-1]:
            await context.bot.send_message(chat_id=chat_id, text=message.content)
            await asyncio.sleep(0.5)  # Have to sleep a bit to prevent rate limits


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


async def spoiler_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command that gets the status of the bot.
    Used for debugging purposes.
    @rtype: object
    """

    if not await _is_admin_user(update, context):
        return

    chat_id = update.effective_chat.id

    msg = "I am spoiler text!"
    entities = [
        MessageEntity(type=MessageEntityType.SPOILER, offset=5, length=7)
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        entities=entities,
    )


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
        CommandHandler(WHISPER_COMMAND, whisper_handler),
        MessageHandler(filters.TEXT & (~filters.COMMAND), listen_for_messages_handler)
    ]


def get_admin_handlers() -> list[BaseHandler]:
    return [
        CommandHandler(REPLAY_COMMAND, replay_messages_handler),
        CommandHandler(STATUS_COMMAND, status_handler),
        CommandHandler("spoiler", spoiler_handler),  # TODO: Remove me afterwards
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
