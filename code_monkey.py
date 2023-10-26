import base64
from io import BytesIO
import os
import random
import sys
import time
import re
from datetime import datetime
import discord

import requests
from discord import ClientUser, Message as DiscordMessage
from database import Database, Chat, Message
from images.stablility_ai import get_image_for_prompt
from llms.dolphin import LLM

from typing import Optional, Tuple


RATE_LIMIT = int(os.environ.get("RATE_LIMIT"))


async def handle_cm_message(
    db: Database,
    lm: LLM,
    bot_user: ClientUser | None,
    message: DiscordMessage,
    partialMessage: DiscordMessage,
) -> None:
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
    content = f"### Server Name: {message.author.display_name}\n\n{content}"

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
        image_seed=0,
    )

    # Add the message to the chat if the chat alreadi exists
    if not new_chat:
        db.add_message(chat.id, new_message)
        # update the chat with the first message id if it has not been set yet
        if chat.first_message_id == 0:
            db.set_first_message_id(chat.id, new_message.id)
    else:
        # If this is a new chat then we need to update the
        # chat with the new message and add the chat to
        # the database
        chat.first_message_id = new_message.id
        db.create_chat(chat)
        db.add_message(chat.id, new_message)

    # retrieve the messages we need to use
    messages = db.get_chat_messages(chat.id)

    print("History: ", [x.id for x in messages])

    # Use the LM to generate a response
    completion = lm.chat_completion(messages)

    # Iterate over the completion adding each token to the response
    response = ""
    for token in completion:
        # Tokens contain spacing between words so we just add the text
        # directly to the response
        response += token

    print("Raw response: ", response, flush=True)

    # Post process the message content by removing ### Server Name: ... from the beginning if it exsits using regex
    response, image_prompt = post_process_response(response)

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
    database_msg_content = response
    if image_prompt:
        database_msg_content = f"<image>{image_prompt}</image>\n{response}"
    res_message = Message(
        id=int(time.time() * 1000),
        content=database_msg_content,
        author="bot",
        timestamp=datetime.now(),
        chat_id=chat.id,
        image_seed=0,
    )
    db.add_message(chat.id, res_message)

    # Respond in the channel
    edit_content = response
    if image_prompt:
        if len(edit_content) > 0:
            edit_content += "\n"
        edit_content += "Generating an image..."
    if len(edit_content) == 0:
        edit_content = "Monkey speechless..."
    await partialMessage.edit(content=edit_content)

    if image_prompt:
        print("Generating an image: ", image_prompt, flush=True)
        # generate seed
        seed = random.randrange(100000)

        # generate the image
        try:
            image_content = get_image_for_prompt(image_prompt, seed)
        except Exception as e:
            print("Error generating image: ", e, flush=True)
            partialMessage.edit(
                content=response + "\nMonkey failed to generate image :("
            )
            return

        if image_content is None:
            partialMessage.edit(
                content=response + "\nMonkey failed to generate image :("
            )
            return

        if image_content == "<|IAC|>":
            image_prompt = None
            response = "Monkey finds your request inappropriate :("
        else:
            print(
                "Image Content: ",
                "empty" if image_content is None else image_content[:10],
                flush=True,
            )
            await partialMessage.reply(
                file=discord.File(
                    BytesIO(base64.b64decode(image_content)),
                    filename=f"GIGO_Code_Monkey_{image_prompt.replace(' ', '_')[:50]}.png",
                    description=image_prompt[:1024],
                )
            )
            db.add_image_to_message(res_message.id, image_content, seed)
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


def post_process_response(response: str) -> Tuple[str, Optional[str]]:
    """
    Clean the output of the llm
    """
    response = re.sub(r"^.*Server Name:\s*", "", response).strip()
    response = (
        response.replace("<|im_end|>", "").replace("<im_start>", "").strip()
    )
    response = (
        response.replace("<|assistant|>", "")
        .replace("<|user|>", "")
        .replace("<|system|>", "")
        .strip()
    )

    # handle image generation
    prompt = None
    if response.startswith("<image>"):
        # extract the prompt between the <image> tags
        start = response.find('<image>') + len('<image>')
        end = response.find('</image>')
        prompt = response[start:end].strip()

        if end != -1:
            # get the content following the </image> tag
            end += len('</image>')
        response = response[end:].strip()

    return response, prompt
