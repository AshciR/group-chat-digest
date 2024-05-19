import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY", "fake-key")  # Need to add a default for the tests to work
open_client_singleton = OpenAI(api_key=api_key)


def get_ai_client() -> OpenAI:
    """
    Returns the GPT client
    @return:
    """
    return open_client_singleton


def summarize_messages_as_paragraph(client: OpenAI, messages: str) -> str:
    """
    Uses ChatGPT to summarize messages and returns the summary in a TL;DR format.
    It needs the messages to be in the following format.
    {Sender}:{Message};{Sender}:{Message};...{Sender}:{Message}
    @param client: The OpenAI client
    @param messages: the messages in the {Sender}:{Message} format
    @return: the summarized messages
    """
    prompt = "You are a secretary. I will give you messages from a group chat in the following format: " \
             "{Sender}: {Message}; {Sender}: {Message}. " \
             "I want you to summarize the messages into paragraphs. " \
             "Assume that the messages are in chronological order. "  \
             "Also, make your best effort to associate messages that have a common theme."

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"{prompt}"},
            {"role": "user", "content": f"{messages}"}
        ]
    )
    return completion.choices[0].message.content


def summarize_messages_as_bullet_points(client: OpenAI, messages: str) -> str:
    """
    Uses ChatGPT to summarize messages and returns the summary in a TL;DR format.
    It needs the messages to be in the following format.
    {Sender}:{Message};{Sender}:{Message};...{Sender}:{Message}
    @param client: The OpenAI client
    @param messages: the messages in the {Sender}:{Message} format
    @return: the summarized messages
    """
    prompt = "You are a secretary. I will give you messages from a group chat in the following format: " \
             "{Sender}: {Message}; {Sender}: {Message}. " \
             "I want you to summarize the messages into bullet points. " \
             "Use hyphens as the bullet points. " \
             "Assume that the messages are in chronological order. "  \
             "Also, make your best effort to associate messages that have a common theme."

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"{prompt}"},
            {"role": "user", "content": f"{messages}"}
        ]
    )
    return completion.choices[0].message.content
