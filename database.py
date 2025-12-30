import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import Config

# Initialize Client
client = MongoClient(Config.MONGO_URI)
db = client['heavy_translator_db']

# Indexes
try:
    db.translation_tasks.create_index([("file_id", 1), ("status", 1)])
    db.translation_tasks.create_index([("file_id", 1), ("page_num", 1)])
except Exception as e:
    logging.warning(f"Could not create indexes: {e}")

def check_connection():
    """Checks MongoDB connection and logs the result."""
    try:
        # The ismaster command is cheap and does not require auth.
        client.admin.command('ismaster')
        logging.info("✅ MongoDB Connection Successful")
        return True
    except ConnectionFailure:
        logging.error("❌ MongoDB Connection Failed")
        return False
    except Exception as e:
        logging.error(f"❌ MongoDB Connection Error: {e}")
        return False

def reset_file_tasks(file_id):
    """Clears existing tasks for a file to start fresh."""
    try:
        db.translation_tasks.delete_many({"file_id": file_id})
        logging.info(f"Reset tasks for file: {file_id}")
    except Exception as e:
        logging.error(f"Error resetting file tasks: {e}")

def save_block(file_id, page_num, text, bbox):
    """Saves a text block to the database."""
    try:
        # Check if exists to avoid duplicates if re-running (though reset should handle it)
        # Using upsert with unique keys if we had them, but here just insert is fine if we reset first.
        # But to be safe, we use update_one with upsert based on bbox logic
        db.translation_tasks.update_one(
            {"file_id": file_id, "page_num": page_num, "bbox": bbox},
            {"$set": {
                "original_text": text,
                "status": "pending",
                "translated_text": None,
                "created_at": logging.Formatter.converter() # simpler than datetime import if not needed
            }},
            upsert=True
        )
    except Exception as e:
        logging.error(f"Error saving block: {e}")

def get_pending_tasks(file_id):
    """Returns all pending tasks for a file."""
    try:
        return list(db.translation_tasks.find({"file_id": file_id, "status": "pending"}))
    except Exception as e:
        logging.error(f"Error getting pending tasks: {e}")
        return []

def update_task_status(task_id, translated_text):
    """Updates a task with translated text and marks as completed."""
    try:
        db.translation_tasks.update_one(
            {"_id": task_id},
            {"$set": {"translated_text": translated_text, "status": "completed"}}
        )
    except Exception as e:
        logging.error(f"Error updating task: {e}")

def get_task_counts(file_id):
    """Returns (total, completed) counts."""
    try:
        total = db.translation_tasks.count_documents({"file_id": file_id})
        completed = db.translation_tasks.count_documents({"file_id": file_id, "status": "completed"})
        return total, completed
    except Exception as e:
        logging.error(f"Error getting counts: {e}")
        return 0, 0

def get_all_completed_tasks(file_id):
    """Returns all completed tasks sorted by page number."""
    try:
        return list(db.translation_tasks.find({"file_id": file_id, "status": "completed"}).sort("page_num", 1))
    except Exception as e:
        logging.error(f"Error getting all completed: {e}")
        return []
