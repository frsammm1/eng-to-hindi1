import time
import logging
from groq import Groq
from config import Config

try:
    groq_client = Groq(api_key=Config.GROQ_API_KEY)
except Exception as e:
    logging.error(f"Failed to initialize Groq client: {e}")
    groq_client = None

def translate_with_retry(text, retries=5):
    if not groq_client:
        logging.error("Groq client not initialized")
        return None

    attempt = 0
    while attempt < retries:
        try:
            chat_completion = groq_client.chat.completions.create(
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
                wait_time = (attempt + 1) * 20 # Progressive backoff: 20, 40, 60...
                logging.warning(f"Rate limit exceeded. Waiting {wait_time}s. Attempt {attempt+1}/{retries}")
                time.sleep(wait_time)
                attempt += 1
            else:
                logging.error(f"Translation error: {e}")
                return None

    logging.error("Max retries exceeded for translation.")
    return None
