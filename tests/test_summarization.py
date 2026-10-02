from unittest.mock import MagicMock

import pytest

from summarization import (
    convert_to_speech, summarize_messages_as_bullet_points, summarize_messages_as_paragraph,
    SummaryGenerationError, SUMMARY_MAX_COMPLETION_TOKENS, SUMMARY_REASONING_EFFORT,
    BULLETS_SYSTEM_PROMPT, PARAGRAPH_SYSTEM_PROMPT
)


def _mock_completion(mocker, content, finish_reason="stop"):
    completion = MagicMock()
    completion.choices[0].message.content = content
    completion.choices[0].finish_reason = finish_reason
    return mocker.patch("summarization.litellm.completion", return_value=completion)


@pytest.mark.parametrize("summarize, system_prompt", [
    (summarize_messages_as_paragraph, PARAGRAPH_SYSTEM_PROMPT),
    (summarize_messages_as_bullet_points, BULLETS_SYSTEM_PROMPT),
])
def test_summarize_messages_returns_the_summary(mocker, summarize, system_prompt):
    # Given: The LLM returns a summary
    mock_completion = _mock_completion(mocker, "Alice and Bob made plans")

    # When: We summarize the messages
    result = summarize(MagicMock(), "[Alice] hi\n[Bob] hello")

    # Then: The summary is returned
    assert result == "Alice and Bob made plans"

    # And: The call leaves room for reasoning tokens
    kwargs = mock_completion.call_args.kwargs
    assert kwargs["max_completion_tokens"] == SUMMARY_MAX_COMPLETION_TOKENS
    assert kwargs["reasoning_effort"] == SUMMARY_REASONING_EFFORT
    assert kwargs["drop_params"] is True
    assert kwargs["messages"][0] == {"role": "system", "content": system_prompt}


@pytest.mark.parametrize("summarize", [summarize_messages_as_paragraph, summarize_messages_as_bullet_points])
@pytest.mark.parametrize("content, finish_reason", [
    ("", "length"),  # Reasoning tokens used up the whole budget
    (None, "stop"),  # No content at all
    ("   \n", "stop"),  # Whitespace only
    ("- Alice proposed hanging", "length"),  # Summary was cut off
])
def test_summarize_messages_raises_when_summary_is_unusable(mocker, summarize, content, finish_reason):
    # Given: The LLM returns an empty or truncated summary
    _mock_completion(mocker, content, finish_reason)

    # When / Then: Summarizing raises an error instead of returning it
    with pytest.raises(SummaryGenerationError):
        summarize(MagicMock(), "[Alice] hi\n[Bob] hello")


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
