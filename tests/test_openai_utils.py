from unittest.mock import MagicMock

import pytest

from openai_utils import convert_to_speech


@pytest.mark.asyncio
async def test_convert_to_speech(mocker, tmp_path):
    # Given: A mocked OpenAI client and text input
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_client.audio.speech.with_streaming_response.create.return_value.__enter__.return_value = mock_response
    mock_response.stream_to_file = MagicMock()

    text = "Hello, this is a test."

    # Mock UUID to produce a predictable filename
    mock_uuid = "1234"
    mocker.patch("uuid.uuid4", return_value=mock_uuid)

    # When: We call the convert_to_speech function
    result = convert_to_speech(mock_client, text, tmp_path)

    # Then: The function returns the correct file path
    expected_directory = tmp_path / "voice_messages"
    expected_file_path = expected_directory / f"speech_{mock_uuid}.mp3"
    assert result == expected_file_path, f"Expected path '{expected_file_path}', but got '{result}'"

    # And: The OpenAI client creates the speech with correct parameters
    mock_client.audio.speech.with_streaming_response.create.assert_called_once_with(
        model="tts-1",
        voice="nova",
        input=text
    )

    # And: The file is streamed to the specified path
    mock_response.stream_to_file.assert_called_once_with(expected_file_path)

    # And: No actual file is created
    assert not result.exists()
