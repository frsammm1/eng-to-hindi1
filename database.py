import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import Config

client = MongoClient(Config.MONGO_URI)
db = client['heavy_translator_db']

def check_connection():
    try:
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        logging.info("MongoDB connection successful.")
        return True
    except ConnectionFailure:
        logging.error("MongoDB connection failed.")
        return False

def save_block(file_id, page_num, text, bbox):
    try:
        return db.translation_tasks.update_one(
            {"file_id": file_id, "bbox": bbox, "page_num": page_num},
            {"$set": {
                "original_text": text,
                "status": "pending",
                "translated_text": None
            }},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Error saving block: {e}")

def save_tasks_bulk(tasks):
    try:
        if not tasks:
            return
        return db.translation_tasks.insert_many(tasks)
    except Exception as e:
        logging.error(f"Error saving tasks bulk: {e}")

def delete_file_tasks(file_id):
    try:
        return db.translation_tasks.delete_many({"file_id": file_id})
    except Exception as e:
        logging.error(f"Error deleting file tasks: {e}")

def get_next_batch(file_id, limit=10):
    try:
        return list(db.translation_tasks.find({"file_id": file_id, "status": "pending"}).limit(limit))
    except Exception as e:
        logging.error(f"Error getting batch: {e}")
        return []

def update_task(task_id, translated_text):
    try:
        db.translation_tasks.update_one(
            {"_id": task_id},
            {"$set": {"translated_text": translated_text, "status": "completed"}}
        )
    except Exception as e:
        logging.error(f"Error updating task: {e}")

def get_completed_count(file_id):
    try:
        return db.translation_tasks.count_documents({"file_id": file_id, "status": "completed"})
    except Exception as e:
        logging.error(f"Error getting completed count: {e}")
        return 0

def get_total_count(file_id):
    try:
        return db.translation_tasks.count_documents({"file_id": file_id})
    except Exception as e:
        logging.error(f"Error getting total count: {e}")
        return 0

def get_recent_completed(file_id, limit=100):
    try:
        return list(db.translation_tasks.find({"file_id": file_id, "status": "completed"}).sort("_id", -1).limit(limit))
    except Exception as e:
        logging.error(f"Error getting recent completed: {e}")
        return []

def get_all_completed(file_id):
    try:
        return list(db.translation_tasks.find({"file_id": file_id, "status": "completed"}).sort("page_num", 1))
    except Exception as e:
        logging.error(f"Error getting all completed: {e}")
        return []
