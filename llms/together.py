import json
import os
from openai import OpenAI, Stream
import tiktoken
from database import Message
from const import ADMIN_INSTRUCTIONS, ADMIN_INSTRUCTIONS_FUNCTION, HERMES2_SYSTEM_MESSAGE
from typing import Any, Iterator, List, Tuple
from transformers import AutoTokenizer


class LLM:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained("NousResearch/Meta-Llama-3.1-8B-Instruct")
        self.client = OpenAI(
            api_key=os.environ["FIREWORKS_API_KEY"],
            base_url="https://api.fireworks.ai/inference/v1",
        )

    @staticmethod
    def get_system_message() -> str:
        return HERMES2_SYSTEM_MESSAGE

    def preprocess_messages(self, messages: List[Message], admin_instructions: List[str] = [], admin: bool = False) -> Tuple[List[dict], int]:
        # Initialize the chat messages with an empty list
        chat_messages = []

        # Handle admin instructions
        if len(admin_instructions) > 0:
            system_message = HERMES2_SYSTEM_MESSAGE.replace("<ADMIN_INSTRUCTIONS>", ADMIN_INSTRUCTIONS.format("\n".join([f"- {instruction}" for instruction in admin_instructions])))
        else:
            system_message = HERMES2_SYSTEM_MESSAGE.replace("<ADMIN_INSTRUCTIONS>", "")
        
        # Handle admin
        if admin:
            system_message = system_message.replace("<ADMIN_INSTRUCTIONS_FUNCTION_CALL>", ADMIN_INSTRUCTIONS_FUNCTION)
        else:
            system_message = system_message.replace("<ADMIN_INSTRUCTIONS_FUNCTION_CALL>", "")

        print(system_message, flush=True)

        # Initialize the token size to the length of the
        # system message
        token_size = len(self.tokenizer.encode(system_message))

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
            if message_token_size + token_size > 15000:
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
                "content": system_message,
            },
        )

        return chat_messages, 16000-token_size

    def chat_completion(self, messages: List[Message], admin_instructions: List[str] = [], admin: bool = False) -> Iterator[str]:
        # Preprocess the chat messages
        chat_messages, max_tokens = self.preprocess_messages(messages, admin_instructions, admin)

        print(json.dumps(chat_messages, indent=2), flush=True)

        # Create a new chat completion to stream the response from the model
        completion = self.client.chat.completions.create(
            messages=chat_messages,
            stream=True,
            temperature=0.7,
            top_p=0.95,
            max_tokens=max_tokens,
            model="accounts/fireworks/models/llama-v3p1-405b-instruct"
        )

        # Iterate over the chat completion to get the response
        # from the model one token at a time
        for t in completion:
            if t.choices[0].delta.content is None:
                continue
            yield t.choices[0].delta.content
