from unittest.mock import MagicMock, Mock

import pytest
from telegram.ext import CommandHandler, MessageHandler

from message_storage import Message
from telegram_bot import (
    format_message_for_openai, get_handlers, summary_handler, gist_handler, help_handler,
    listen_for_messages_handler, whisper_gist_handler, start_handler, get_admin_handlers,
    replay_messages_handler,
    status_handler, broadcast_handler, whisper_handler, does_user_want_a_voice_message, does_message_contain_spoilers,
    analytics_handler
)

from telegram.constants import MessageEntityType


@pytest.mark.asyncio
async def test_format_message_for_openai():
    # Given: We have messages
    messages = [
        Message(message_id=1, content="Hello", owner_id=1, owner_name="Alice", created_at="2023-05-14T12:00:00Z"),
        Message(message_id=2, content="Hi", owner_id=2, owner_name="Bob", created_at="2023-05-14T12:01:00Z"),
        Message(message_id=3, content="Bye?", owner_id=3, owner_name="Charlie", created_at="2023-05-14T12:02:00Z")
    ]

    # When: We format the messages
    result = await format_message_for_openai(messages)

    # Then: They're formatted correctly
    expected_result = "Alice: Hello;Bob: Hi;Charlie: Bye?"
    assert result == expected_result, f"Expected '{expected_result}', but got '{result}'"


@pytest.mark.asyncio
@pytest.mark.parametrize("args, expected", [
    (["5", "voice"], True),  # 'voice' as the second argument
    (["voice", "something"], True),  # 'voice' as the first argument
    (["5", "something"], False),  # 'voice' is not present
    (["something", "other", "voice"], False),  # 'voice' is not in the first or second position
    (["something"], False),  # Only one argument, not 'voice'
    ([], False)  # No arguments provided
])
async def test_does_user_want_a_voice_message(args, expected):
    # Given: A mock context with the specified args
    context = MagicMock()
    context.args = args

    # When: Calling does_user_want_a_voice_message
    result = await does_user_want_a_voice_message(context)

    # Then: Assert that the result matches the expected outcome
    assert result == expected


def test_get_handlers():
    handlers = get_handlers()

    assert len(handlers) == 7, "Expected 7 handlers"

    # Test CommandHandlers
    assert isinstance(handlers[0], CommandHandler)
    assert handlers[0].commands == frozenset({'start'})
    assert handlers[0].callback == start_handler

    assert isinstance(handlers[1], CommandHandler)
    assert handlers[1].commands == frozenset({'gist'})
    assert handlers[1].callback == gist_handler

    assert isinstance(handlers[2], CommandHandler)
    assert handlers[2].commands == frozenset({'summary'})
    assert handlers[2].callback == summary_handler

    assert isinstance(handlers[3], CommandHandler)
    assert handlers[3].commands == frozenset({'help'})
    assert handlers[3].callback == help_handler

    assert isinstance(handlers[4], CommandHandler)
    assert handlers[4].commands == frozenset({'whspr'})
    assert handlers[4].callback == whisper_gist_handler

    assert isinstance(handlers[5], CommandHandler)
    assert handlers[5].commands == frozenset({'whisper'})
    assert handlers[5].callback == whisper_handler

    # Test MessageHandler
    assert isinstance(handlers[6], MessageHandler)
    assert handlers[6].callback == listen_for_messages_handler


def test_get_admin_handlers():
    handlers = get_admin_handlers()

    assert len(handlers) == 4, "Expected 4 handlers"

    # Test CommandHandlers
    assert isinstance(handlers[0], CommandHandler)
    assert handlers[0].commands == frozenset({'replay'})
    assert handlers[0].callback == replay_messages_handler

    assert isinstance(handlers[1], CommandHandler)
    assert handlers[1].commands == frozenset({'status'})
    assert handlers[1].callback == status_handler

    assert isinstance(handlers[2], CommandHandler)
    assert handlers[2].commands == frozenset({'alert'})
    assert handlers[2].callback == broadcast_handler

    assert isinstance(handlers[3], CommandHandler)
    assert handlers[3].commands == frozenset({'analytics'})
    assert handlers[3].callback == analytics_handler


@pytest.mark.asyncio
async def test_does_message_contain_spoilers_with_spoiler_entity():
    # Given: A message with a spoiler entity

    update_with_spoiler = Mock()
    update_with_spoiler.message = Mock()
    update_with_spoiler.message.entities = [Mock(type=MessageEntityType.SPOILER)]

    # When: We check if it contains spoilers
    result = does_message_contain_spoilers(update_with_spoiler.message)

    # Then: The function should return True
    assert result is True, "Expected True, but got False"


@pytest.mark.asyncio
async def test_does_message_contain_spoilers_without_spoiler_entity():
    # Given: A message without any spoiler entity

    update_without_spoiler = Mock()
    update_without_spoiler.message = Mock()
    update_without_spoiler.message.entities = [Mock(type=MessageEntityType.BOLD)]

    # When: We check if it contains spoilers
    result = does_message_contain_spoilers(update_without_spoiler.message)

    # Then: The function should return False
    assert result is False, "Expected False, but got True"


@pytest.mark.asyncio
async def test_does_message_contain_spoilers_empty_entities():
    # Given: A message with an empty entities list

    update_empty_entities = Mock()
    update_empty_entities.message = Mock()
    update_empty_entities.message.entities = []

    # When: We check if it contains spoilers
    result = does_message_contain_spoilers(update_empty_entities.message)

    # Then: The function should return False
    assert result is False, "Expected False, but got True"


@pytest.mark.asyncio
async def test_does_message_contain_spoilers_multiple_entities_with_spoiler():
    # Given: A message with multiple entities, one of which is a spoiler

    update_mixed_entities_with_spoiler = Mock()
    update_mixed_entities_with_spoiler.message = Mock()
    update_mixed_entities_with_spoiler.message.entities = [
        Mock(type=MessageEntityType.BOLD),
        Mock(type=MessageEntityType.SPOILER),
        Mock(type=MessageEntityType.ITALIC)
    ]

    # When: We check if it contains spoilers
    result = does_message_contain_spoilers(update_mixed_entities_with_spoiler.message)

    # Then: The function should return True
    assert result is True, "Expected True, but got False"


@pytest.mark.asyncio
async def test_does_message_contain_spoilers_multiple_entities_without_spoiler():
    # Given: A message with multiple entities, none of which are spoilers

    update_mixed_entities_without_spoiler = Mock()
    update_mixed_entities_without_spoiler.message = Mock()
    update_mixed_entities_without_spoiler.message.entities = [
        Mock(type=MessageEntityType.BOLD),
        Mock(type=MessageEntityType.ITALIC)
    ]

    # When: We check if it contains spoilers
    result = does_message_contain_spoilers(update_mixed_entities_without_spoiler.message)

    # Then: The function should return False
    assert result is False, "Expected False, but got True"
