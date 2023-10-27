from transformers import AutoTokenizer
from text_generation import Client
from database import Message
from const import SYSTEM_MESSAGE
import random
import os
from typing import Iterator, List


AIROBOROS_FUNC_DEFS = """
Available functions:
generate_image:
  description: Generate images from thorough descriptions using Stable Diffusion XL
  params:
    prompt: (string) a detailed and thorough description of the image that will be generated"""


class LLM:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained(
            'jondurbin/airoboros-m-7b-3.1.2'
        )

        self.client = Client(base_url=os.environ.get("TXT_GEN_URL"))

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

        # add the functions to the last user message
        # chat_messages[-1] += AIROBOROS_FUNC_DEFS

        # format the input for the model's chat template
        content = self.tokenizer.apply_chat_template(chat_messages, tokenize=False)

        # get input token count
        input_tokens = len(self.tokenizer.encode(content))

        print(
            "--------------------------------------------------------------------------------",
            flush=True
        )
        print(
            content,
            flush=True
        )
        print(
            "--------------------------------------------------------------------------------",
            flush=True
        )

        # Create a new chat completion to stream the response from the model
        completion = self.client.generate_stream(
            prompt=content,
            temperature=1.31,
            top_p=0.14,
            repetition_penalty=1.17,
            top_k=49,
            max_new_tokens=4096 - input_tokens,
            stop_sequences=["</s>"],
            seed=random.randint(0, 100000),
        )

        # Iterate over the chat completion to get the response
        # from the model one token at a time
        for t in completion:
            # The first response does not contain a token so we need to
            # to skip any chunk from the model that does not contain a token
            if (
                t.token.text == ""
                or t.token.special
                or t.token.text == "[/INST]"
            ):
                continue
            yield t.token.text
