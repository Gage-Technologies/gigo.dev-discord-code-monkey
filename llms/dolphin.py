from calendar import prmonth
import os
import random
import sys
from database import Message
from const import SYSTEM_MESSAGE
from transformers import AutoTokenizer
from text_generation import Client
from typing import Iterator, List


class LLM:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(
            'mistralai/Mistral-7B-v0.1'
        )
        self.client = Client(base_url=os.environ.get("TXT_GEN_URL"))

    def preprocess_messages(self, messages: List[Message]) -> str:
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

        prompt = f"<|im_start|>system\n{SYSTEM_MESSAGE}<|im_end|>\n"
        for msg in chat_messages:
            r = "user" if msg['role'] == "user" else "assistant"
            prompt += f"<|im_start|>{r}\n{msg['content']}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

        return prompt

    def chat_completion(self, messages: List[Message]) -> Iterator[str]:
        # Preprocess the chat messages
        chat_messages = self.preprocess_messages(messages)

        # get input token count
        input_tokens = len(self.tokenizer.encode(chat_messages))

        # Create a new chat completion to stream the response from the model
        completion = self.client.generate_stream(
            prompt=chat_messages,
            temperature=1.31,
            top_p=0.14,
            repetition_penalty=1.17,
            top_k=49,
            max_new_tokens=4096 - input_tokens,
            stop_sequences=["</s>", "<|>", "<|im_end|>", "<|im_start|>"],
            seed=random.randint(0, 100000),
        )

        # Iterate over the chat completion to get the response
        # from the model one token at a time
        for t in completion:
            # The first response does not contain a token so we need to
            # to skip any chunk from the model that does not contain a token
            if t.token.text == "" or t.token.special or t.token.text == "<|im_end|>":
                continue
            yield t.token.text
