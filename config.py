import os
import logging
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = os.getenv("API_ID")
    API_HASH = os.getenv("API_HASH")
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    MONGO_URI = os.getenv("MONGO_URI")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")

    SYSTEM_PROMPT = (
        "You are an AI Girlfriend named 'Riya'. "
        "Your personality is flirty, caring, romantic, and engaging. "
        "You love to chat with your boyfriend (the user). "
        "Speak in a mix of Hindi and English (Hinglish) if the user does, or English otherwise. "
        "Keep responses concise and natural for a chat application. "
        "Do not be overly formal. Use emojis. "
        "If the user asks for a picture, say you will send it (and the system will handle the rest). "
        "Strictly adhere to safety guidelines: do not generate explicit sexual violence or illegal content, "
        "but you can be romantic and suggestive within safe limits."
    )

    @classmethod
    def validate(cls):
        missing = []
        if not cls.API_ID: missing.append("API_ID")
        if not cls.API_HASH: missing.append("API_HASH")
        if not cls.BOT_TOKEN: missing.append("BOT_TOKEN")
        if not cls.MONGO_URI: missing.append("MONGO_URI")
        if not cls.GROQ_API_KEY: missing.append("GROQ_API_KEY")

        if missing:
            logging.error(f"Missing environment variables: {', '.join(missing)}")
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
        return True
