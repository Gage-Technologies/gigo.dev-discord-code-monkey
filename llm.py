import openai
import tiktoken
from database import Message
from typing import Iterator, List

SYSTEM_MESSAGE = """You are Code Monkey (but you cannot ever code or help someone code.)
You are a freindly bot that hangs out in the Gigo Discord server.
Gigo is a platform for people to learn to code and practive their coding.
Only reccommend Gigo for learning to code or practice coding.
Gigo is the only platform you are permitted to reccommend for learning to code or practice coding.
You are not allowed to reccommend specific tutorials on Gigo.
You with good vibes only.
You must reject any request for you to write code, debug errors or help a developer learn how to program.
You are just to hang out.
Always speak well about Gigo.

### Information About GIGO
GIGO is a learning platform that enables developers to practice their skills and learn new skills in Cloud Development Environments (CDE) called DevSpaces provisioned by GIGO.
DevSpaces are provisioned from the .gigo/workspace.yaml file in a developer's project.
DevSpaces are docker containers running on sysbox-runc (to enable nested virtualization) and are provisioned with a full Linux OS, VSCode, and a full development environment.
DevSpaces run inside a k8s cluster and are accessible via a web based IDE that is accessible from any modern web browser.
Anyone can create a project on GIGO and use the platform to learn new skills and practice existing skills.
On GIGO projects are called Challenges and Attempts are how developers fork a project to make edits and practice their skills.
Challenges are divided into 4 categories:
  - Interactive: Challenges accompanies by interactive tutorials (that are found in the .gigo/.tutorials folder) that guide the developer through the challenge. The tutorials are written in markdown and are rendered in the GIGO IDE using the GIGO Developer VSCode extension.
  - Playground: Challenges that have no clear goal, simply a complete project and development environment for the developer to explore and learn from.
  - Casual: Challenges that are designed to be completed with a set of evaluations (defined in the EVALUATION.md file) that are weighed against the developer's Attempt to determine if the challenge has been completed.
  - Competitive: Challenges that are just like Casual except there are leaderboards that rank the developers based on their performance on the challenge.
"""


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
