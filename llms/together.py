import json
import os
from openai import OpenAI, Stream
import tiktoken
from database import Message
from const import HERMES2_SYSTEM_MESSAGE
from typing import Any, Iterator, List
from transformers import AutoTokenizer

from images.replicate_playground_v2 import PlaygroundV2Params


TOGETHER_SYSTEM_MESSAGE_FORMATTED = HERMES2_SYSTEM_MESSAGE.replace(
    "<GEN_PARAMS>", PlaygroundV2Params.schema_json(indent=2)
)


class LLM:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen1.5-72B-Chat")
        self.client = OpenAI(
            api_key=os.environ["TOGETHER_API_KEY"],
            base_url="https://api.together.xyz",
        )

    @staticmethod
    def get_system_message() -> str:
        schema = PlaygroundV2Params.schema_json(indent=2)
        lines = schema.split("\n")
        formatted_schema = []
        for i, l in enumerate(lines):
            if i != 0:
                l = "  " + l
            formatted_schema.append(l)

        return HERMES_SYSTEM_MESSAGE.replace(
            "<GEN_PARAMS>", "\n".join(formatted_schema)
        )

    def preprocess_messages(self, messages: List[Message]) -> List[dict]:
        # Initialize the chat messages with an empty list
        chat_messages = []

        # Initialize the token size to the length of the
        # system message
        token_size = len(self.tokenizer.encode(TOGETHER_SYSTEM_MESSAGE_FORMATTED))

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
            if message_token_size + token_size > 8192:
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
                "content": TOGETHER_SYSTEM_MESSAGE_FORMATTED,
            },
        )

        return chat_messages

    def chat_completion(self, messages: List[Message]) -> Iterator[str]:
        # Preprocess the chat messages
        chat_messages = self.preprocess_messages(messages)

        print(json.dumps(chat_messages, indent=2), flush=True)

        # Create a new chat completion to stream the response from the model
        completion = self.client.chat.completions.create(
            messages=chat_messages,
            stream=True,
            temperature=0.5,
            top_p=0.95,
            model="Qwen/Qwen1.5-72B-Chat",
        )

        # Iterate over the chat completion to get the response
        # from the model one token at a time
        for t in completion:
            if t.choices[0].delta.content is None:
                continue
            yield t.choices[0].delta.content
