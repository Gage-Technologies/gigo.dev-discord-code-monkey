from calendar import prmonth
import os
import random
import sys
from database import Message
from const import HERMES_SYSTEM_MESSAGE
from transformers import AutoTokenizer
from text_generation import Client
from typing import Iterator, List

from images.stablility_ai import SDXLParams


HERMES_SYSTEM_MESSAGE_FORMATTED = HERMES_SYSTEM_MESSAGE.replace(
    "<GEN_PARAMS>", SDXLParams.schema_json(indent=2)
)


class LLM:
    def __init__(self) -> None:
        self.tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-v0.1")
        # have to do it this way because the official repo has a broken added_tokens.json file
        self.tokenizer.add_tokens(["<|im_end|>", "<|im_start|>"])
        self.client = Client(base_url=os.environ.get("TXT_GEN_URL"))

    @staticmethod
    def get_system_message() -> str:
        schema = SDXLParams.schema_json(indent=2)
        lines = schema.split("\n")
        formatted_schema = []
        for i, l in enumerate(lines):
            if i != 0:
                l = "  " + l
            formatted_schema.append(l)

        return HERMES_SYSTEM_MESSAGE.replace(
            "<GEN_PARAMS>", "\n".join(formatted_schema)
        )

    def preprocess_messages(self, messages: List[Message]) -> str:
        # Initialize the chat messages with an empty list
        chat_messages = []

        # Initialize the token size to the length of the
        # system message
        token_size = len(self.tokenizer.encode(HERMES_SYSTEM_MESSAGE_FORMATTED))

        # double the token size if there are more than 2 messages because we duplicate the system message
        # if len(messages) >= 2:
        #     token_size *= 2

        # Iterate over the messages in reverse order
        # formatting them into a list of ChatCompletionMessage
        # objects
        for message in reversed(messages):
            # Calculate the token size of the message
            message_token_size = len(self.tokenizer.encode(message.content))

            # If the token size of the message is greater than
            # the maximum context size of the model then we
            # will skip the message
            if message_token_size > 1000:
                continue

            # If the token size of the message is greater than
            # the remaining token size then we will skip the
            # message
            if message_token_size > 3000 - token_size:
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

        prompt = f"<|im_start|>system\n{HERMES_SYSTEM_MESSAGE_FORMATTED}<|im_end|>\n"
        for i, msg in enumerate(chat_messages):
            r = "user" if msg["role"] == "user" else "assistant"
            prompt += f"<|im_start|>{r}\n{msg['content']}<|im_end|>\n"

            # if this is the 2nd to last message and there are more than 2 messages
            # we duplicate the system message again to remind the bot
            # if len(chat_messages) > 1 and i == len(chat_messages) - 2:
            #     prompt += f"<|im_start|>system\n{SYSTEM_MESSAGE}<|im_end|>\n"
        prompt += "<|im_start|>assistant\n"

        return prompt

    def chat_completion(self, messages: List[Message]) -> Iterator[str]:
        # Preprocess the chat messages
        chat_messages = self.preprocess_messages(messages)

        print(
            "--------------------------------------------------------------------------------",
            flush=True,
        )
        print(chat_messages, flush=True)
        print(
            "--------------------------------------------------------------------------------",
            flush=True,
        )

        # get input token count
        input_tokens = len(self.tokenizer.encode(chat_messages))

        # Create a new chat completion to stream the response from the model
        completion = self.client.generate_stream(
            prompt=chat_messages,
            temperature=1.31,
            top_p=0.14,
            repetition_penalty=1.17,
            top_k=49,
            max_new_tokens=8096 - input_tokens,
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


if __name__ == "__main__":
    print(LLM.get_system_message())
