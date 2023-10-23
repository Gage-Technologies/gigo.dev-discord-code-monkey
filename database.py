import time
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase


class Message(BaseModel):
    id: int
    content: str
    author: str
    timestamp: datetime
    chat_id: int


class Chat(BaseModel):
    id: int
    author_id: int
    first_message_id: int
    messages: List[Message]
    created_at: datetime
    channel_id: int


class Database:
    def __init__(self, uri: str, db_name: str) -> None:
        self.client: MongoClient = MongoClient(uri)
        self.db: MongoDatabase = self.client[db_name]
        self.chats: Collection = self.db['chats']

    def create_chat(self, chat: Chat) -> Optional[int]:
        chat_dict = chat.dict()
        result = self.chats.insert_one(chat_dict)
        return chat.id if result and result.inserted_id else None

    def get_chat(self, chat_id: int) -> Optional[Chat]:
        chat = self.chats.find_one({'id': chat_id})
        return Chat(**chat) if chat else None

    def get_last_channel_chat(self, author_id: int, channel_id: int) -> Optional[Chat]:
        chats = self.chats.find_one(
            {'channel_id': channel_id, "author_id": author_id}, sort=[('created_at', -1)]
        )
        return Chat(**chats) if chats else None
    
    def set_first_message_id(self, chat_id: int, message_id: int) -> None:
        self.chats.update_one({'id': chat_id}, {'$set': {'first_message_id': message_id}})

    def add_message(self, chat_id: int, message: Message) -> None:
        self.chats.update_one(
            {'id': chat_id}, {'$push': {'messages': message.dict()}}
        )

    def get_message_count_by_time(self, chat_id: int, age: int) -> int:
        # Get the chat by its ID
        chat = self.get_chat(chat_id)
        if chat is None:
            return 0  # Return 0 if the chat doesn't exist

        # Filter messages newer than the cutoff_time
        recent_messages = [
            msg for msg in chat.messages if msg.timestamp.timestamp() > time.time() - age
        ]

        return len(recent_messages)

    def delete_all_chats(self):
        self.chats.delete_many({})
