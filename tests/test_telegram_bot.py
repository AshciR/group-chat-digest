from typing import Tuple

import pytest
from telegram.ext import CommandHandler, MessageHandler

from message_storage import Message, SpoilerRange
from telegram_bot import format_message_for_openai, get_handlers, summary_handler, gist_handler, help_handler, \
    listen_for_messages_handler, whisper_handler, start_handler, get_admin_handlers, replay_messages_handler, \
    status_handler, modify_content_for_spoilers, unwrap_spoiler_content


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

    assert len(handlers) == 6, "Expected 6 handlers"

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
    assert handlers[4].callback == whisper_handler

    # Test MessageHandler
    assert isinstance(handlers[5], MessageHandler)
    assert handlers[5].callback == listen_for_messages_handler


def test_get_admin_handlers():
    handlers = get_admin_handlers()

    assert len(handlers) == 2, "Expected 2 handlers"

    # Test CommandHandlers
    assert isinstance(handlers[0], CommandHandler)
    assert handlers[0].commands == frozenset({'replay'})
    assert handlers[0].callback == replay_messages_handler

    assert isinstance(handlers[1], CommandHandler)
    assert handlers[1].commands == frozenset({'status'})
    assert handlers[1].callback == status_handler


@pytest.mark.parametrize(
    "text, ranges, expected",
    [
        # Single spoiler
        ("I have apples, and I have bananas, yay", [SpoilerRange(7, 6)], "I have ^apples^, and I have bananas, yay"),
        # Replace ^ with *
        ("I ^am a spoiler", [SpoilerRange(3, 2)], "I *^am^ a spoiler"),
        # No spoilers
        ("No spoilers here", [], "No spoilers here"),
        # Mixed ^ and Spoilers
        ("I am ^not^ a spoiler", [SpoilerRange(11, 3)], "I am *not* ^a s^poiler"),
        # Multiple spoilers
        ("Multiple spoilers here", [SpoilerRange(0, 8), SpoilerRange(18, 4)], "^Multiple^ spoilers ^here^"),
        # Multiple spoilers but ranges are not in correct order
        ("Multiple spoilers here", [SpoilerRange(18, 4), SpoilerRange(0, 8)], "^Multiple^ spoilers ^here^"),
        # Multiple spoilers mixed with *
        ("Multiple ^spoilers^ here", [SpoilerRange(0, 8), SpoilerRange(20, 4)], "^Multiple^ *spoilers* ^here^"),
        # Edge cases
        ("Edge cases", [SpoilerRange(0, 4), SpoilerRange(5, 5)], "^Edge^ ^cases^"),
    ]
)
def test_modify_content_for_spoilers(text: str, ranges, expected: str):
    # Given: We have text content from messages

    # When: We modify it
    modified_content = modify_content_for_spoilers(text, ranges)

    # Then: Then it should be modified corrected
    assert modified_content == expected


@pytest.mark.parametrize("wrapped_summary, expected_text, expected_ranges", [
    ("This is a ^spoiler^ text example.",
     "This is a spoiler text example.",
     [SpoilerRange(start_index=10, length=7)]),

    ("This is a ^spoiler^ text example with multiple ^spoilers^ in it.",
     "This is a spoiler text example with multiple spoilers in it.",
     [SpoilerRange(start_index=10, length=7), SpoilerRange(start_index=45, length=8)]),

    ("No spoilers here.",
     "No spoilers here.",
     []),

    ("^One big spoiler^",
     "One big spoiler",
     [SpoilerRange(start_index=0, length=15)]),

    ("^Spoilers^ at the start and the ^end^",
     "Spoilers at the start and the end",
     [SpoilerRange(start_index=0, length=8), SpoilerRange(start_index=30, length=3)])
])
def test_unwrap_spoiler_content(wrapped_summary, expected_text, expected_ranges):
    # Given: We have spoiler text content from messages

    # When: We unwrap it
    unwrapped_text, spoiler_ranges = unwrap_spoiler_content(wrapped_summary)

    # Then: Then it should be unwrapped correctly with the spoiler ranges
    assert unwrapped_text == expected_text
    assert spoiler_ranges == expected_ranges
