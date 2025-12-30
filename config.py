import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGO_URI = os.getenv("MONGO_URI")
    SESSION_STRING = os.getenv("SESSION_STRING", "") # Optional: For Userbot capabilities
    OWNER_ID = int(os.getenv("OWNER_ID", "0")) # Optional: Restrict usage to owner

    @classmethod
    def validate(cls):
        missing = []
        if not cls.API_ID: missing.append("API_ID")
        if not cls.API_HASH: missing.append("API_HASH")
        # We allow BOT_TOKEN and SESSION_STRING to be empty for interactive login
        if not cls.MONGO_URI: missing.append("MONGO_URI")

        if missing:
            logging.error(f"Missing environment variables: {', '.join(missing)}")
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
        return True
