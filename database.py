import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client['heavy_translator_db']

def save_block(file_id, page_num, text, bbox, block_type):
    # block_type: 'question', 'option', 'explanation'
    return db.translation_tasks.update_one(
        {"file_id": file_id, "bbox": bbox, "page_num": page_num},
        {"$set": {
            "original_text": text,
            "block_type": block_type,
            "status": "pending",
            "translated_text": None
        }},
        upsert=True
    )

def get_next_batch(file_id, limit=10):
    return list(db.translation_tasks.find({"file_id": file_id, "status": "pending"}).limit(limit))

def update_task(task_id, translated_text):
    db.translation_tasks.update_one(
        {"_id": task_id},
        {"$set": {"translated_text": translated_text, "status": "completed"}}
    )
  
