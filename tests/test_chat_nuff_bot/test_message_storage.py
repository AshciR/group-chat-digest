from datetime import datetime

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
        created_at=datetime.now().isoformat()
    )

    # When: We store a message
    result = store_message(stub_redis_client, chat_id, message)

    # Then: The chat should have 1 message
    assert result == 1


def test_store_message_does_not_bleed_into_other_chat(stub_redis_client):
    # Given: There is 1 message in Chat A
    chat_a_id = -100
    message_a_1_id = 150
    message_a_1_content = f"Test message chat: {chat_a_id}, id: {message_a_1_id}"
    message_a_1, _ = _create_test_message(stub_redis_client, chat_a_id, message_a_1_id, content=message_a_1_content)

    # And: There are 2 messages in Chat B
    chat_b_id = -200
    message_b_1_id = 250
    message_b_1_content = f"Test message chat: {chat_b_id}, id: {message_b_1_id}"
    message_b_1, _ = _create_test_message(stub_redis_client, chat_b_id, message_b_1_id, content=message_b_1_content)

    message_b_2_id = 251
    message_b_2_content = f"Test message chat: {chat_b_id}, id: {message_b_2_id}"
    message_b_2, _ = _create_test_message(stub_redis_client, chat_b_id, message_b_2_id, content=message_b_2_content)

    # When: We store another message in Chat B
    message_b_3_id = message_b_2_id + 1
    last_message = Message(
        message_id=message_b_2_id + 1,
        content=f"Test message chat: {chat_b_id}, id: {message_b_3_id}",
        owner_id=901,
        owner_name='Unit Tester',
        created_at=datetime.now().isoformat()
    )
    result = store_message(stub_redis_client, chat_b_id, last_message)

    # Then: Chat B should have 3 messages
    assert result == 3
    # Note: There were 4 messages created, but the method returns the number
    # of messages for the chat. Hence, Chat B should have 3.


def test_store_message_only_keeps_latest_messages():
    # Given: There are maximum messages for the chat
    # When: We store another message
    # Then: The chat should have maximum messages
    # TODO: Saving this one for Alrick
    pass


@pytest.fixture
def stub_redis_client(request):
    redis_client = FakeRedis()
    return redis_client


def _create_test_message(stub_redis_client: FakeRedis,
                         chat_id: int,
                         message_id: int,
                         owner_id: int = 901,
                         content: str = "I am a test message"
                         ) -> tuple[Message, int]:
    """
    Creates a test message.

    @param stub_redis_client:
    @param chat_id:
    @param message_id:
    @param owner_id:
    @param content:
    @return: the created message and the number of messages in the queue
    """

    message = Message(
        message_id=message_id,
        content=content,
        owner_id=owner_id,
        owner_name='Unit Tester',
        created_at=datetime.now().isoformat()
    )

    result = store_message(stub_redis_client, chat_id, message)
    assert result != 0, "Message was not created during test setup"

    return message, result
