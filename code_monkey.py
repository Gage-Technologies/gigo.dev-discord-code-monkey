import time
import re
from datetime import datetime
from discord import ClientUser, Message as DiscordMessage
from database import Database, Chat, Message
from llm import LLM


async def handle_cm_message(
    db: Database,
    lm: LLM,
    bot_user: ClientUser | None,
    message: DiscordMessage,
    partialMessage: DiscordMessage,
) -> None:
    if message.author == bot_user:
        return
    
    content = re.sub(r"<@\d+>", " ", message.content)

    # create a new chat if the message is clear
    if content.strip() == "clear":
        db.create_chat(
            Chat(
                id=int(time.time() * 1000),
                author_id=message.author.id,
                channel_id=message.channel.id,
                messages=[],
                created_at=datetime.now(),
                first_message_id=0,
            )
        )
        await partialMessage.edit(content="Monkey forgot!")
        return

    # Retrieve the last chat for this channel from the database
    chat = db.get_last_channel_chat(message.author.id, message.channel.id)

    # If there is not chat then we need to create one
    new_chat = False
    if chat is None:
        new_chat = True
        chat = Chat(
            id=int(time.time() * 1000),
            author_id=message.author.id,
            channel_id=message.channel.id,
            messages=[],
            created_at=datetime.now(),
            first_message_id=0,
        )

    # reject if we have more than 5 messages in 2 minutes
    msg_count = db.get_message_count_by_time(chat.id, 2 * 60)

    if msg_count > 5:
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
