from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_ai_client() -> OpenAI:
    """
    Returns the GPT client
    @return:
    """
    client = OpenAI()
    return client


def summarize_messages_using_ai(client: OpenAI, messages: str) -> str:
    """
    Uses ChatGPT to summarize messages and returns the summary in a TL;DR format.
    It needs the messages to be in the following format.
    {Sender}:{Message};{Sender}:{Message};...{Sender}:{Message}
    @param client: The OpenAI client
    @param messages: the messages in the {Sender}:{Message} format
    @return: the summarized messages
    """
    prompt = "You are a secretary. I will give you messages from a group chat in the following format: " \
             "{Sender}: {Message}; {Sender}: {Message}." \
             "I want you to summarize the messages into a TL;DR format. " \
             "Assume that the messages are in chronological order."  \
             "Also, make your best effort to associate messages that have a common theme." \
             "After you summarize the messages, return the main talking points as a String with each " \
             "point separated by a newline character."

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"{prompt}"},
            {"role": "user", "content": f"{messages}"}
        ]
    )
    return completion.choices[0].message.content
