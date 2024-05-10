from datetime import datetime

import pytest
from fakeredis import FakeRedis

from message_storage import (
    Message,
    store_message,
    DEFAULT_MESSAGE_STORAGE,
    chat_exists,
    get_latest_n_messages,
    configure_message_storage
)


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


def test_store_message_only_keeps_latest_messages(stub_redis_client):
    # Given: There are maximum messages for the chat
    chat_id = -100
    messages_and_count: list[tuple[Message, int]] = [
        _create_test_message(stub_redis_client, chat_id, msg_id, content=f"Test message chat: {chat_id}, id: {msg_id}")
        for msg_id in range(DEFAULT_MESSAGE_STORAGE + 1)
    ]

    # When: We store another message
    last_message = messages_and_count[-1][0]
    next_message = Message(
        message_id=last_message.message_id + 1,
        content=f"Test message chat: {chat_id}, id: {last_message.message_id + 1}",
        owner_id=901,
        owner_name='Unit Tester',
        created_at=datetime.now().isoformat()
    )
    result = store_message(stub_redis_client, chat_id, next_message)

    # Then: The chat should have maximum messages
    assert result == DEFAULT_MESSAGE_STORAGE


def test_chat_exists(stub_redis_client):
    # Given: We have a message for a chat
    chat_id = -100
    message_id = 150
    content = f"Test message chat: {chat_id}, id: {message_id}"
    message, _ = _create_test_message(stub_redis_client, chat_id, message_id, content=content)

    # When: We check if the chat exists
    exists = chat_exists(stub_redis_client, chat_id)

    # Then: It should be true
    assert exists


def test_chat_does_not_exist(stub_redis_client):
    # Given: The chat doesn't exist
    non_existent_chat_id = -999

    # When: We check if the chat exists
    exists = chat_exists(stub_redis_client, non_existent_chat_id)

    # Then: It should be False
    assert not exists


def test_get_latest_n_messages(stub_redis_client):
    # Given: We have 10 messages
    chat_id = -100
    created_messages_and_count: list[tuple[Message, int]] = [
        _create_test_message(stub_redis_client, chat_id, msg_id, content=f"Test message chat: {chat_id}, id: {msg_id}")
        for msg_id in range(10)
    ]

    # When: We get 5 messages
    latest_messages = get_latest_n_messages(stub_redis_client, chat_id, 5)

    # Then: It should be the latest 5
    # Last created message will be the 1st index
    assert len(latest_messages) == 5
    assert latest_messages[0].content == created_messages_and_count[-1][0].content


def test_get_latest_n_messages_for_non_existent_chat(stub_redis_client):
    # Given: The chat doesn't exist
    non_existent_chat_id = -999

    # When: We get 5 messages
    latest_messages = get_latest_n_messages(stub_redis_client, non_existent_chat_id, 5)

    # Then: It should be 0
    assert len(latest_messages) == 0


@pytest.mark.parametrize("num_of_msgs", [0, -1])
def test_get_latest_n_messages_when_n_is_invalid(stub_redis_client, num_of_msgs):
    # Given: We have 10 messages
    chat_id = -100
    for msg_id in range(10):
        _create_test_message(stub_redis_client, chat_id, msg_id, content=f"Test message chat: {chat_id}, id: {msg_id}")

    # When: We get an invalid number of messages
    latest_messages = get_latest_n_messages(stub_redis_client, chat_id, num_of_msgs)

    # Then: It should be an empty list
    assert len(latest_messages) == 0


def test_configure_message_storage_success(mocker):
    # Given: We have valid configs
    mocker.patch(
        'os.getenv', side_effect=lambda x, default=None: {'REDIS_HOST': 'localhost',
                                                          'REDIS_PORT': '6379',
                                                          'REDIS_DB': '0',
                                                          'REDIS_USE_TLS': 'False',
                                                          'REDIS_TIMEOUT': '5'}.get(x, default)
    )

    mock_redis = mocker.patch('message_storage.Redis')
    mock_redis.return_value.ping.return_value = True

    # Expect: Connection to be successful
    assert configure_message_storage()


def test_configure_message_storage_fail_ping(mocker):
    # Given: We have valid configs
    mocker.patch('os.getenv', side_effect=lambda x: {'REDIS_HOST': 'localhost',
                                                     'REDIS_PORT': '6379',
                                                     'REDIS_DB': '0',
                                                     'REDIS_USE_TLS': 'False',
                                                     'REDIS_TIMEOUT': '5'}.get(x))

    mock_redis = mocker.patch('message_storage.Redis')
    mock_redis.return_value.ping.return_value = False

    # Expect: Connection to be successful
    assert not configure_message_storage()


def test_configure_message_storage_timeout(mocker):
    # Given: We have valid configs
    mocker.patch('os.getenv', side_effect=lambda x: {'REDIS_HOST': 'localhost',
                                                     'REDIS_PORT': '6379',
                                                     'REDIS_DB': '0',
                                                     'REDIS_USE_TLS': 'False',
                                                     'REDIS_TIMEOUT': '5'}.get(x))

    mock_redis = mocker.patch('message_storage.Redis')

    # When: The cache doesn't connect within time
    mock_redis.side_effect = TimeoutError

    # Then: We get a False
    assert not configure_message_storage()


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
