import os
import uuid
from pathlib import Path

import litellm
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5.4-mini")
openai_api_key = os.getenv("OPENAI_API_KEY", "fake-key")  # Need to add a default for the tests to work
open_client_singleton = OpenAI(api_key=openai_api_key)


def get_ai_client() -> OpenAI:
    """
    Returns the OpenAI client (used for TTS). Summarization calls go through LiteLLM
    and ignore this client, but the parameter is preserved for signature compatibility.
    """
    return open_client_singleton


def summarize_messages_as_paragraph(client: OpenAI, messages: str) -> str:
    """
    Uses an LLM (via LiteLLM) to summarize messages and returns the summary in a TL;DR format.
    It needs the messages to be in the following format.
    {Sender}:{Message};{Sender}:{Message};...{Sender}:{Message}
    @param client: Unused — kept for signature compatibility.
    @param messages: the messages in the {Sender}:{Message} format
    @return: the summarized messages
    """
    prompt = "You are a secretary. I will give you messages from a group chat in the following format: " \
             "{Sender}: {Message}; {Sender}: {Message}. " \
             "I want you to summarize the messages into paragraphs. " \
             "Assume that the messages are in chronological order. " \
             "Also, make your best effort to associate messages that have a common theme."

    completion = litellm.completion(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": f"{prompt}"},
            {"role": "user", "content": f"{messages}"}
        ]
    )
    return completion.choices[0].message.content


def summarize_messages_as_bullet_points(client: OpenAI, messages: str) -> str:
    """
    Uses an LLM (via LiteLLM) to summarize messages and returns the summary in a TL;DR format.
    It needs the messages to be in the following format.
    {Sender}:{Message};{Sender}:{Message};...{Sender}:{Message}
    @param client: Unused — kept for signature compatibility.
    @param messages: the messages in the {Sender}:{Message} format
    @return: the summarized messages
    """
    prompt = "You are a secretary. I will give you messages from a group chat in the following format: " \
             "{Sender}: {Message}; {Sender}: {Message}. " \
             "I want you to summarize the messages into bullet points. " \
             "Use hyphens as the bullet points. " \
             "Assume that the messages are in chronological order. " \
             "Also, make your best effort to associate messages that have a common theme."

    completion = litellm.completion(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": f"{prompt}"},
            {"role": "user", "content": f"{messages}"}
        ]
    )
    return completion.choices[0].message.content


def ping_openai(client: OpenAI) -> str:
    """
    Used to test the status of the bot.
    @param client: Unused — kept for signature compatibility.
    @return:
    """

    prompt = "I am pinging you to determine if you are functional. " \
             "Respond with a HTTP status code, and the response time"

    message = "Ping"
    try:
        completion = litellm.completion(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": f"{prompt}"},
                {"role": "user", "content": f"{message}"}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"


def convert_to_speech(client: OpenAI, text: str, base_dir: Path = Path(__file__).parent) -> Path:
    """
    Converts a given text input into speech, saves it as an audio file in MP3 format,
    and returns the file path.

    This function uses the provided OpenAI client to generate a speech audio file
    from the specified text. The audio file is saved with a unique filename in
    a 'voice_messages' directory created within the script's directory, if it
    doesn't already exist.

    Args:
        client (OpenAI): The OpenAI client instance used to generate speech from text.
        text (str): The text content to be converted into speech.
        base_dir (Path): The base directory for saving the voice message (for testing or custom paths).

    Returns:
        Path: The file path of the generated speech audio file.

    Raises:
        Exception: If there is an issue with the speech generation or file streaming.
    """

    # Create a directory called 'voice_messages' if it doesn't exist
    voice_messages_dir = base_dir / "voice_messages"
    voice_messages_dir.mkdir(exist_ok=True)

    # Generate a unique filename using UUID
    voice_message = f"speech_{uuid.uuid4()}.mp3"
    speech_file_path = voice_messages_dir / voice_message

    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=text
    ) as response:
        response.stream_to_file(speech_file_path)
    return speech_file_path
