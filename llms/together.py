import json
import os
from openai import OpenAI, Stream
import tiktoken
from database import Message
from const import HERMES2_SYSTEM_MESSAGE
from typing import Any, Iterator, List, Tuple
from transformers import AutoTokenizer

from images.sd3 import SD3Params


class LLM:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-70B-Instruct")
        self.client = OpenAI(
            api_key=os.environ["TOGETHER_API_KEY"],
            base_url="https://api.together.xyz",
        )

    @staticmethod
    def get_system_message() -> str:
        return HERMES2_SYSTEM_MESSAGE

    def preprocess_messages(self, messages: List[Message]) -> Tuple[List[dict], int]:
        # Initialize the chat messages with an empty list
        chat_messages = []

        # Initialize the token size to the length of the
        # system message
        token_size = len(self.tokenizer.encode(HERMES2_SYSTEM_MESSAGE))

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
            if message_token_size + token_size > 7000:
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
                "content": HERMES2_SYSTEM_MESSAGE,
            },
        )

        return chat_messages, 8100-token_size

    def chat_completion(self, messages: List[Message]) -> Iterator[str]:
        # Preprocess the chat messages
        chat_messages, max_tokens = self.preprocess_messages(messages)

        print(json.dumps(chat_messages, indent=2), flush=True)

        # Create a new chat completion to stream the response from the model
        completion = self.client.chat.completions.create(
            messages=chat_messages,
            stream=True,
            temperature=0.7,
            top_p=0.95,
            max_tokens=max_tokens,
            model="meta-llama/Llama-3-70b-chat-hf",
        )

        # Iterate over the chat completion to get the response
        # from the model one token at a time
        for t in completion:
            if t.choices[0].delta.content is None:
                continue
            yield t.choices[0].delta.content
