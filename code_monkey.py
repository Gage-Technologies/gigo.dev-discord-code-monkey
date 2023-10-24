import os
import time
import re
from datetime import datetime

import requests
from discord import ClientUser, Message as DiscordMessage
from database import Database, Chat, Message
from llms.dolphin import LLM


RATE_LIMIT = int(os.environ.get("RATE_LIMIT"))


async def handle_cm_message(
    db: Database,
    lm: LLM,
    bot_user: ClientUser | None,
    message: DiscordMessage,
    partialMessage: DiscordMessage,
) -> None:
    # Check if the message was sent by the bot
    if message.author == bot_user:
        return

    # prep the message content
    content = re.sub(r"<@\d+>", " ", message.content)

    # create a new chat if the message is clear
    if content.strip() == "clear":
        db.create_chat(
            Chat(
                id=int(time.time() * 1000),
                author_id=0,
                channel_id=message.channel.id,
                messages=[],
                created_at=datetime.now(),
                first_message_id=0,
            )
        )
        await partialMessage.edit(content="Monkey forgot!")
        return

    # prepend the username
    content = (
        f"### Server Name: {message.author.display_name}\n\n{message.content}"
    )

    # Retrieve the last chat for this channel from the database
    chat = db.get_last_channel_chat(0, message.channel.id)

    # If there is not chat then we need to create one
    new_chat = False
    if chat is None:
        new_chat = True
        chat = Chat(
            id=int(time.time() * 1000),
            author_id=0,
            channel_id=message.channel.id,
            messages=[],
            created_at=datetime.now(),
            first_message_id=0,
        )

    # reject if we have more than RATE_LIMIT messages in 2 minutes
    if RATE_LIMIT > 0:
        msg_count = db.get_message_count_by_time(chat.id, 2 * 60)

        if msg_count > RATE_LIMIT:
            await partialMessage.edit(
                content="Monkey can't think that fast! Wait 2m before trying again..."
            )
            return

    # Create a new message object
    new_message = Message(
        id=int(time.time() * 1000),
        content=content,
        author=message.author.name,
        timestamp=datetime.now(),
        chat_id=chat.id,
    )

    # Add the message to the chat if the chat alreadi exists
    if not new_chat:
        db.add_message(chat.id, new_message)
        # append the message to the chat object since we only updates
        # the database not the model we currently have in memory
        chat.messages.append(new_message)

        # update the chat with the first message id if it has not been set yet
        if chat.first_message_id == 0:
            db.set_first_message_id(chat.id, new_message.id)
    else:
        # If this is a new chat then we need to update the
        # chat with the new message and add the chat to
        # the database
        chat.first_message_id = new_message.id
        chat.messages.append(new_message)
        db.create_chat(chat)

    # Use the LM to generate a response
    completion = lm.chat_completion(chat.messages)

    # Iterate over the completion adding each token to the response
    response = ""
    for token in completion:
        # Tokens contain spacing between words so we just add the text
        # directly to the response
        response += token

    # Post process the message content by removing ### Server Name: ... from the beginning if it exsits using regex
    response = post_process_response(response)

    # Check if the response is longer than 2000 characters
    if len(response) > 2000:
        main_content = response[:1500]

        # Upload the remainder to Pastebin
        paste_url = upload_to_pastebin(response)
        if paste_url:
            response = main_content + f"\n... [Read more]({paste_url})"
        else:
            response = (
                main_content
                + "\n... [Content too long, cannot display the rest.]"
            )

    # Save the response to the database
    db.add_message(
        chat.id,
        Message(
            id=int(time.time() * 1000),
            content=response,
            author="bot",
            timestamp=datetime.now(),
            chat_id=chat.id,
        ),
    )

    # Respond in the channel
    await partialMessage.edit(content=response)


def upload_to_pastebin(content: str) -> str:
    """
    Upload the provided content to Pastebin and return the URL.
    """
    PASTEBIN_API_URL = "https://pastebin.com/api/api_post.php"

    payload = {
        "api_dev_key": os.environ.get("PASTEBIN_API_KEY"),
        "api_option": "paste",
        "api_paste_code": content,
    }
    response = requests.post(PASTEBIN_API_URL, data=payload)

    if response.status_code == 200:
        return response.text
    else:
        print(
            f"Failed to upload to Pastebin. Status Code: {response.status_code}, Response: {response.text}"
        )
        return None


def post_process_response(response: str) -> str:
    """
    Clean the output of the llm
    """
    response = re.sub(r"^.*Server Name:\s*", "", response).strip()
    response = response.replace("<|im_end|>").replace("<im_start>").strip()
    response = (
        response.replace("<|assistant|>")
        .replace("<|user|>")
        .replace("<|system|>")
        .strip()
    )
    return response
