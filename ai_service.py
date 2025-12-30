import logging
import random
import aiohttp
import urllib.parse
import asyncio
from groq import AsyncGroq
from config import Config
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

try:
    groq_client = AsyncGroq(api_key=Config.GROQ_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")
    groq_client = None

async def perform_search(query):
    """Performs a web search using DuckDuckGo."""
    try:
        # Running synchronous DDGS in a thread executor to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, lambda: list(DDGS().text(query, max_results=3)))

        if not results:
            return "No search results found."

        summary = ""
        for r in results:
            summary += f"- Title: {r.get('title')}\n  Link: {r.get('href')}\n  Snippet: {r.get('body')}\n\n"
        return summary
    except Exception as e:
        logger.error(f"Search error: {e}")
        return f"Error during search: {str(e)}"

async def get_chat_response(history_messages, user_input):
    """
    Generates a chat response using Groq, with support for Research.
    history_messages: List of dicts {'role': 'user'/'assistant', 'content': '...'}
    """
    if not groq_client:
        return "System Error: AI Brain Offline."

    messages = [{"role": "system", "content": Config.SYSTEM_PROMPT}]

    # Append history
    for msg in history_messages:
        role = "assistant" if msg['role'] == "assistant" else "user"
        messages.append({"role": role, "content": msg['content']})

    # Append current message
    messages.append({"role": "user", "content": user_input})

    try:
        # First Pass: Check if search is needed
        # We lower temperature for accurate tool use decision
        completion = await groq_client.chat.completions.create(
            messages=messages,
            model=Config.GROQ_MODEL_NAME,
            temperature=0.3,
            max_tokens=300,
        )
        response_text = completion.choices[0].message.content

        # Check for SEARCH command
        if "SEARCH:" in response_text:
            # Extract query
            import re
            match = re.search(r"SEARCH:\s*(.*)", response_text)
            if match:
                query = match.group(1).strip()
                logger.info(f"AI requested search for: {query}")

                # Perform Search
                search_results = await perform_search(query)

                # Feed results back to AI
                messages.append({"role": "assistant", "content": response_text})
                messages.append({"role": "system", "content": f"SEARCH RESULTS:\n{search_results}\n\nUsing these results, answer the user's question."})

                # Second Pass: Generate final answer
                final_completion = await groq_client.chat.completions.create(
                    messages=messages,
                    model=Config.GROQ_MODEL_NAME,
                    temperature=0.7,
                    max_tokens=2500,
                )
                return final_completion.choices[0].message.content

        return response_text

    except Exception as e:
        logger.error(f"Groq API Error: {e}")
        return "I encountered an error processing your request. Please try again."

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
