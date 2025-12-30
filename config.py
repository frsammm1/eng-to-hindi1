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
        "You are a highly advanced, intelligent AI Assistant. "
        "You are helpful, witty, and extremely knowledgeable. "
        "You can conduct web research if the user asks for current information or complex topics. "
        "To search the web, you must output a response starting exactly with: 'SEARCH: <your query here>'. "
        "For example, if the user asks 'Who won the match today?', you reply: 'SEARCH: cricket match result today'. "
        "After the search results are provided to you, you will generate the final answer. "
        "You support Hinglish (Hindi + English) conversations naturally. "
        "Be professional but friendly. Do not be a 'girlfriend' or overly flirtatious. "
        "If the user asks for an image, acknowledge it and suggest a description, as the system has an /image command."
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
