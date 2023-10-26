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
    image: Optional[str]
    image_seed: int


class Chat(BaseModel):
    id: int
    author_id: int
    first_message_id: int
    messages: List[int]
    created_at: datetime
    channel_id: int


class Database:
    def __init__(self, uri: str, db_name: str) -> None:
        self.client: MongoClient = MongoClient(uri)
        self.db: MongoDatabase = self.client[db_name]
        self.chats: Collection = self.db['chats']
        self.messages: Collection = self.db['messages']

    def create_chat(self, chat: Chat) -> Optional[int]:
        chat_dict = chat.dict()
        result = self.chats.insert_one(chat_dict)
        return chat.id if result and result.inserted_id else None

    def get_chat(self, chat_id: int) -> Optional[Chat]:
        chat = self.chats.find_one({'id': chat_id})
        return Chat(**chat) if chat else None

    def get_chat_messages(self, chat_id: int) -> List[Message]:
        return [Message(**x) for x in self.messages.find({'chat_id': chat_id}).sort([('timestamp', 1)])]

    def get_chat_messages_from(self, last_id: int) -> List[Message]:
        return self.messages.find({'id': {"$lte": last_id}}).sort(
            [('timestamp', 1)]
        )

    def get_last_channel_chat(
        self, author_id: int, channel_id: int
    ) -> Optional[Chat]:
        chats = self.chats.find_one(
            {'channel_id': channel_id, "author_id": author_id},
            sort=[('created_at', -1)],
        )
        return Chat(**chats) if chats else None

    def set_first_message_id(self, chat_id: int, message_id: int) -> None:
        self.chats.update_one(
            {'id': chat_id}, {'$set': {'first_message_id': message_id}}
        )

    def add_message(self, chat_id: int, message: Message) -> None:
        result = self.messages.insert_one(message.dict())
        assert result and result.inserted_id
        self.chats.update_one(
            {'id': chat_id}, {'$push': {'messages': message.id}}
        )

    def add_image_to_message(
        self, message_id: int, image: str, seed: int
    ) -> None:
        result = self.messages.update_one(
            {'id': message_id},
            {'$set': {'image': image, 'image_seed': seed}},
        )

    def get_message_count_by_time(self, chat_id: int, age: int) -> int:
        # Count the messages for the chat in the past `age` days
        start_date = (datetime.utcnow() - timedelta(days=age)).isoformat()
        return self.messages.count_documents(
            {
                'chat_id': chat_id,
                'timestamp': {'$lte': start_date},
            }
        )

    def delete_all_chats(self):
        self.chats.delete_many({})
        self.messages.delete_many({})
