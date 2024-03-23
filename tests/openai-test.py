from openai import OpenAI
from dotenv import load_dotenv


def open_ai_hello_world():
    load_dotenv()
    client = OpenAI()
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative "
                        "flair."},
            {"role": "user", "content": "Compose a poem that explains the concept of recursion in programming."}
        ]
    )
    print(completion.choices[0].message)


if __name__ == '__main__':
    open_ai_hello_world()
