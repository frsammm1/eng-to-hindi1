import asyncio
import logging
from groq import AsyncGroq
from config import Config

# Initialize Async Client
try:
    groq_client = AsyncGroq(api_key=Config.GROQ_API_KEY)
except Exception as e:
    logging.error(f"Failed to initialize Groq client: {e}")
    groq_client = None

async def translate_text(text, retries=5):
    """
    Translates text to Hindi using Groq API asynchronously.
    Handles Rate Limits (429) with exponential backoff.
    """
    if not groq_client:
        logging.error("Groq client not initialized")
        return None

    attempt = 0
    while attempt < retries:
        try:
            chat_completion = await groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an SSC GS Expert. Translate the following English text to Hindi. Preserve technical terms. Output ONLY the translated text."},
                    {"role": "user", "content": text}
                ],
                model="llama3-70b-8192",
                temperature=0.2,
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg: # Rate Limit
                wait_time = (attempt + 1) * 10  # Backoff: 10s, 20s, 30s...
                logging.warning(f"Rate limit exceeded (429). Waiting {wait_time}s. Attempt {attempt+1}/{retries}")
                await asyncio.sleep(wait_time)
                attempt += 1
            else:
                logging.error(f"Translation error: {e}")
                # Some errors might be transient, but others (like auth) are not.
                # For now, we assume simple network glitches might be retriable, but complex API errors not.
                # If it's not 429, we often shouldn't retry immediately unless it's a timeout.
                # Let's retry on timeouts too?
                # For simplicity and robustness, if it's not 429, we probably fail this task.
                return None

    logging.error("Max retries exceeded for translation.")
    return None
