import pytest
from datetime import datetime, timedelta
from database import Database, Chat, Message


@pytest.fixture
def database():
    return Database(uri='mongodb://root:rootpassword@localhost:27017', db_name='discord_bot_test')


def test_create_chat(database):
    # Create a dummy chat
    chat = Chat(id=1, first_message_id=1, messages=[], created_at=datetime.now(), channel_id=1)

    # Insert the chat into the database
    chat_id = database.create_chat(chat)

    # Verify that the chat was inserted
    assert chat_id is not None

def test_get_chat(database):
    # Create a dummy chat
    chat = Chat(id=1, first_message_id=1, messages=[], created_at=datetime.now(), channel_id=1)

    # Insert the chat into the database
    chat_id = database.create_chat(chat)

    # Retrieve the chat from the database
    retrieved_chat = database.get_chat(chat_id)

    # Verify that the retrieved chat matches the original chat
    assert retrieved_chat.id == chat.id
    assert retrieved_chat.first_message_id == chat.first_message_id
    assert retrieved_chat.messages == chat.messages

    # Clean up the database
    database.delete_all_chats()

def test_get_last_channel_chat(database):
    # Create two dummy chats
    chat1 = Chat(id=1, first_message_id=1, messages=[], created_at=datetime.now(), channel_id=1)
    chat2 = Chat(id=2, first_message_id=2, messages=[], created_at=datetime.now() + timedelta(days=0, hours=0, minutes=30), channel_id=1)

    # Insert the chats into the database
    chat_id1 = database.create_chat(chat1)
    chat_id2 = database.create_chat(chat2)

    # Retrieve the last chat from the database
    retrieved_chat = database.get_last_channel_chat(1)

    # Verify that the retrieved chat matches the original chat
    assert retrieved_chat.id == chat2.id
    assert retrieved_chat.first_message_id == chat2.first_message_id
    assert retrieved_chat.messages == chat2.messages

    # Clean up the database
    database.delete_all_chats()

def test_add_message(database):
    # Create a dummy chat
    chat = Chat(id=1, first_message_id=1, messages=[], created_at=datetime.now(), channel_id=1)

    # Insert the chat into the database
    chat_id = database.create_chat(chat)

    # Create a dummy message
    message = Message(id=1, content='Hello, world!', author='user', timestamp=datetime.now(), chat_id=chat_id)

    # Add the message to the chat
    database.add_message(chat_id, message)

    # Retrieve the chat from the database
    retrieved_chat = database.get_chat(chat_id)

    # Verify that the message was added to the chat
    assert len(retrieved_chat.messages) == 1
    assert retrieved_chat.messages[0].id == message.id
    assert retrieved_chat.messages[0].content == message.content
    assert retrieved_chat.messages[0].author == message.author
    assert retrieved_chat.messages[0].chat_id == message.chat_id

    # Clean up the database
    database.delete_all_chats()