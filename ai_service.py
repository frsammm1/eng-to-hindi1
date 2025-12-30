import logging
import random
import aiohttp
import urllib.parse
from groq import AsyncGroq
from config import Config

logger = logging.getLogger(__name__)

try:
    groq_client = AsyncGroq(api_key=Config.GROQ_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")
    groq_client = None

async def get_chat_response(history_messages, user_input):
    """
    Generates a chat response using Groq.
    history_messages: List of dicts {'role': 'user'/'assistant', 'content': '...'}
    """
    if not groq_client:
        return "Sorry, my brain is offline right now! 😵‍💫"

    messages = [{"role": "system", "content": Config.SYSTEM_PROMPT}]
    # Append history (limit context window if needed, done in db fetch)
    for msg in history_messages:
        role = "assistant" if msg['role'] == "assistant" else "user"
        messages.append({"role": role, "content": msg['content']})

    # Append current message
    messages.append({"role": "user", "content": user_input})

    try:
        completion = await groq_client.chat.completions.create(
            messages=messages,
            model=Config.GROQ_MODEL_NAME,
            temperature=0.8, # Higher temperature for more creative/flirty responses
            max_tokens=250,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return "Baby, I'm having a bit of a headache... can you say that again? 🥺"

async def generate_image(prompt):
    """
    Generates an image using Pollinations.ai (No key required).
    Returns the URL of the image.
    """
    # Enhance prompt for better results
    enhanced_prompt = f"realistic, high quality, 4k, {prompt}, beautiful lighting, detailed"
    encoded_prompt = urllib.parse.quote(enhanced_prompt)

    # Random seed to ensure variety
    seed = random.randint(1, 100000)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&nologo=true"

    # Verify the URL works (optional, but good practice)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return url
        except Exception as e:
            logger.error(f"Image generation error: {e}")

    return None
