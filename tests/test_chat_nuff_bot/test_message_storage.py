import pytest
from fakeredis import FakeRedis

from chat_nuff_bot.message_storage import Message, store_message


def test_store_message(stub_redis_client):
    # Given: There are no messages for the chat
    chat_id = -100

    # And: We have a message
    message = Message(
        message_id=150,
        content='I am a test message',
        owner_id=901,
        owner_name='Unit Tester',
        created_at='2024-05-03T13:33:00.306657'
    )

    # When: We store a message
    result = store_message(stub_redis_client, chat_id, message)

    # Then: The chat should have 1 message
    assert result == 1


def test_store_message_does_not_bleed_into_other_chat():
    # Given: There is 1 message in Chat A
    # And: There are 2 messages in Chat B
    # When: We store another message in Chat B
    # Then: Chat B should have 3 messages
    pass


def test_store_message_only_keeps_latest_messages():
    # Given: There are maximum messages for the chat
    # When: We store another message
    # Then: The chat should have maximum messages
    pass


@pytest.fixture
def stub_redis_client(request):
    redis_client = FakeRedis()
    return redis_client
