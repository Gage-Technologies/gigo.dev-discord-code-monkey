import openai
import tiktoken
from database import Message
from const import SYSTEM_MESSAGE
from typing import Iterator, List


class LLM:
    def __init__(self) -> None:
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

    def preprocess_messages(self, messages: List[Message]) -> List[dict]:
        # Initialize the chat messages with an empty list
        chat_messages = []

        # Initialize the token size to the length of the
        # system message
        token_size = len(self.tokenizer.encode(SYSTEM_MESSAGE))

        # Iterate over the messages in reverse order
        # formatting them into a list of ChatCompletionMessage
        # objects
        for message in reversed(messages):
            # Calculate the token size of the message
            message_token_size = len(self.tokenizer.encode(message.content))

            # If the token size of the message is greater than
            # the maximum context size of the model then we
            # will skip the message
            if message_token_size > 2048:
                continue

            # If the token size of the message is greater than
            # the remaining token size then we will skip the
            # message
            if message_token_size > 2048 - token_size:
                continue

            # Add the message to the chat messages
            chat_messages.append(
                {
                    # Set the role to assistant if the message is from the bot
                    "role": "assistant" if message.author == "bot" else "user",
                    "content": message.content,
                }
            )

            # Update the token size
            token_size += message_token_size

        # Reverse the chat messages so that they are in
        # chronological order
        chat_messages.reverse()

        # Add the system message to the beginning of the chat messages
        chat_messages.insert(
            0,
            {
                "role": "system",
                "content": SYSTEM_MESSAGE,
            },
        )

        return chat_messages

    def chat_completion(self, messages: List[Message]) -> Iterator[str]:
        # Preprocess the chat messages
        chat_messages = self.preprocess_messages(messages)

        # Create a new chat completion to stream the response from the model
        completion = openai.ChatCompletion.create(
            messages=chat_messages,
            stream=True,
            temperature=1,
            top_p=0,
            model="gpt-3.5-turbo",
        )

        # Iterate over the chat completion to get the response
        # from the model one token at a time
        for t in completion:
            # The first response does not contain a token so we need to
            # to skip any chunk from the model that does not contain a token
            if "content" not in t["choices"][0]["delta"].keys():
                continue
            yield t["choices"][0]["delta"]["content"]
