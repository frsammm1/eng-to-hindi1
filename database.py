from pymongo import MongoClient
from config import Config
import logging

logger = logging.getLogger(__name__)

client = None
db = None
chats_collection = None

def check_connection():
    global client, db, chats_collection
    try:
        client = MongoClient(Config.MONGO_URI)
        db = client.get_database() # Connect to default DB in URI
        chats_collection = db['chat_history']
        # Test command
        client.admin.command('ping')
        logger.info("Connected to MongoDB")
        return True
    except Exception as e:
        logger.error(f"MongoDB Connection Error: {e}")
        return False

def get_chat_history(user_id, limit=10):
    if chats_collection is None: return []
    try:
        # Retrieve last N messages
        cursor = chats_collection.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        history = list(cursor)
        return history[::-1] # Reverse to chronological order
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return []

import datetime

def add_message(user_id, role, content):
    if chats_collection is None: return
    try:
        message = {
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.utcnow()
        }
        chats_collection.insert_one(message)
    except Exception as e:
        logger.error(f"Error adding message: {e}")

def clear_history(user_id):
    if chats_collection is None: return
    try:
        chats_collection.delete_many({"user_id": user_id})
    except Exception as e:
        logger.error(f"Error clearing history: {e}")
