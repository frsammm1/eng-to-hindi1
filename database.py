from pymongo import MongoClient
from config import Config
import logging
import datetime

logger = logging.getLogger(__name__)

client = None
db = None
jobs_collection = None

def check_connection():
    global client, db, jobs_collection
    try:
        client = MongoClient(Config.MONGO_URI)
        try:
            db = client.get_database()
        except Exception:
            db = client['transfer_bot']

        jobs_collection = db['transfer_jobs']
        client.admin.command('ping')
        logger.info("Connected to MongoDB")
        return True
    except Exception as e:
        logger.error(f"MongoDB Connection Error: {e}")
        return False

def create_job(user_id, source, dest, start_id, end_id):
    """Creates a new transfer job."""
    if jobs_collection is None: return None
    job = {
        "user_id": user_id,
        "source": source,
        "dest": dest,
        "start_id": int(start_id),
        "end_id": int(end_id),
        "current_id": int(start_id),
        "status": "active", # active, cancelled, completed, failed
        "total_count": int(end_id) - int(start_id) + 1,
        "processed": 0,
        "failed": 0,
        "start_time": datetime.datetime.utcnow(),
        "last_updated": datetime.datetime.utcnow()
    }
    result = jobs_collection.insert_one(job)
    return str(result.inserted_id)

def get_active_job(user_id):
    """Gets the currently active job for a user."""
    if jobs_collection is None: return None
    return jobs_collection.find_one({"user_id": user_id, "status": "active"})

def update_job_progress(job_id, current_id, success=True):
    """Updates the progress of a job."""
    if jobs_collection is None: return

    update_fields = {
        "current_id": current_id,
        "last_updated": datetime.datetime.utcnow()
    }
    inc_fields = {"processed": 1}
    if not success:
        inc_fields["failed"] = 1

    jobs_collection.update_one(
        {"_id": job_id},
        {"$set": update_fields, "$inc": inc_fields}
    )

def cancel_job(user_id):
    """Cancels active job for user."""
    if jobs_collection is None: return
    jobs_collection.update_many(
        {"user_id": user_id, "status": "active"},
        {"$set": {"status": "cancelled", "end_time": datetime.datetime.utcnow()}}
    )

def complete_job(job_id):
    """Marks job as completed."""
    if jobs_collection is None: return
    jobs_collection.update_one(
        {"_id": job_id},
        {"$set": {"status": "completed", "end_time": datetime.datetime.utcnow()}}
    )
