import pytest

# from message_storage import Message
# from telegram_bot import format_message_for_openai


# @pytest.mark.asyncio
# async def test_format_message_for_openai():
#
#     # Given: We have messages
#     messages = [
#         Message(message_id=1, content="Hello", owner_id=1, owner_name="Alice", created_at="2023-05-14T12:00:00Z"),
#         Message(message_id=2, content="Hi", owner_id=2, owner_name="Bob", created_at="2023-05-14T12:01:00Z"),
#         Message(message_id=3, content="Bye?", owner_id=3, owner_name="Charlie", created_at="2023-05-14T12:02:00Z")
#     ]
#
#     # When: We format the messages
#     result = await format_message_for_openai(messages)
#
#     # Then: They're formatted correctly
#     expected_result = "Alice: Hello;Bob: Hi;Charlie: Bye?"
#     assert result == expected_result, f"Expected '{expected_result}', but got '{result}'"


def test_foo():
    assert True
