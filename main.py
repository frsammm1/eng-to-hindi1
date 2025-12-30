import logging
import asyncio
import re
import pyrogram
from pyrogram import Client, filters
from config import Config
from database import check_connection, get_chat_history, add_message, clear_history
from ai_service import get_chat_response, generate_image

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validate Config
Config.validate()

# Check Database Connection
if not check_connection():
    logger.error("Could not connect to MongoDB. Exiting...")
    exit(1)

app = Client(
    "ssc_heavy_bot", # Keeping session name same to reuse session if needed
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

async def send_chunked_message(message, text):
    """Splits long text into chunks to respect Telegram's limit."""
    limit = 4096
    if len(text) <= limit:
        await message.reply(text)
        return

    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break

        # Find split point
        split_at = text.rfind('\n', 0, limit)
        if split_at == -1:
            split_at = text.rfind(' ', 0, limit)
        if split_at == -1:
            split_at = limit

        parts.append(text[:split_at])
        text = text[split_at:].lstrip()

    for part in parts:
        await message.reply(part)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    # Clear old history on start for a fresh conversation
    clear_history(user_id)

    welcome_text = (
        "Hello! I am your Advanced AI Assistant. 🤖\n"
        "I can help you with questions, research topics online, and even generate images.\n\n"
        "• Chat with me in English or Hindi (Hinglish).\n"
        "• Ask me about current events (I can search the web! 🌐).\n"
        "• Use `/image [description]` to generate AI art.\n\n"
        "How can I assist you today?"
    )
    add_message(user_id, "assistant", welcome_text)
    await message.reply(welcome_text)

@app.on_message(filters.command("reset"))
async def reset_command(client, message):
    clear_history(message.from_user.id)
    await message.reply("Memory wiped! Starting a fresh session. 🔄")

@app.on_message(filters.command("image"))
async def image_command(client, message):
    if len(message.command) < 2:
        await message.reply("Please provide a description! Example: `/image futuristic city at night`")
        return

    prompt = message.text.split(None, 1)[1]
    status_msg = await message.reply("Generating image... please wait. 🎨")
    
    try:
        image_url = await generate_image(prompt)
        if image_url:
            await message.reply_photo(image_url, caption=f"Generated: '{prompt}'")
            await status_msg.delete()
        else:
            await status_msg.edit("Failed to generate image. Please try again.")
    except Exception as e:
        logger.error(f"Image command error: {e}")
        await status_msg.edit("Something went wrong, sorry!")

@app.on_message(filters.text & filters.private)
async def chat_handler(client, message):
    user_id = message.from_user.id
    user_input = message.text


    # 1. Get History (before adding current message to avoid duplication in context)
    history = get_chat_history(user_id, limit=10)

    # 2. Save User Message
    add_message(user_id, "user", user_input)

    # 3. Generate Response
    # Send "typing" action
    await client.send_chat_action(message.chat.id, pyrogram.enums.ChatAction.TYPING)

    response_text = await get_chat_response(history, user_input)

    # 4. Save & Send Response
    add_message(user_id, "assistant", response_text)
    await send_chunked_message(message, response_text)

if __name__ == "__main__":
    logger.info("Advanced AI Assistant Started...")
    app.run()
