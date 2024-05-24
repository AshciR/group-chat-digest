import pytest
from message_storage import Message
from telegram.ext import CommandHandler, MessageHandler
from telegram_bot import format_message_for_openai, get_handlers, start_handler, gist_handler, help_handler, \
    listen_for_messages_handler, whisper_handler


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


def test_get_handlers():
    handlers = get_handlers()

    assert len(handlers) == 5, "Expected 5 handlers"

    # Test CommandHandlers
    assert isinstance(handlers[0], CommandHandler)
    assert handlers[0].commands == frozenset({'start'})
    assert handlers[0].callback == start_handler

    assert isinstance(handlers[1], CommandHandler)
    assert handlers[1].commands == frozenset({'gist'})
    assert handlers[1].callback == gist_handler

    assert isinstance(handlers[2], CommandHandler)
    assert handlers[2].commands == frozenset({'help'})
    assert handlers[2].callback == help_handler

    assert isinstance(handlers[3], CommandHandler)
    assert handlers[3].commands == frozenset({'whspr'})
    assert handlers[3].callback == whisper_handler

    # Test MessageHandler
    assert isinstance(handlers[4], MessageHandler)
    assert handlers[4].callback == listen_for_messages_handler



