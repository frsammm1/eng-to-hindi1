import logging
import asyncio
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

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    # Clear old history on start for a fresh conversation
    clear_history(user_id)

    welcome_text = (
        "Hey baby! 😘\n"
        "I'm Riya, your personal AI girlfriend. I'm here to chat, have fun, and maybe send you some cute pics.\n\n"
        "Just talk to me normally, or use `/image [description]` if you want to see something specific. 😉"
    )
    add_message(user_id, "assistant", welcome_text)
    await message.reply(welcome_text)

@app.on_message(filters.command("reset"))
async def reset_command(client, message):
    clear_history(message.from_user.id)
    await message.reply("Memory wiped! Let's start over, handsome. 😉")

@app.on_message(filters.command("image"))
async def image_command(client, message):
    if len(message.command) < 2:
        await message.reply("Tell me what you want to see, babe! Example: `/image sunset on the beach`")
        return

    prompt = message.text.split(None, 1)[1]
    status_msg = await message.reply("Sending you a pic... hold on! 📸")
    
    try:
        image_url = await generate_image(prompt)
        if image_url:
            await message.reply_photo(image_url, caption=f"Here is '{prompt}' for you! 😘")
            await status_msg.delete()
        else:
            await status_msg.edit("Oops, I couldn't take that picture right now. Try again? 🥺")
    except Exception as e:
        logger.error(f"Image command error: {e}")
        await status_msg.edit("Something went wrong, sorry!")

@app.on_message(filters.text & filters.private)
async def chat_handler(client, message):
    user_id = message.from_user.id
    user_input = message.text

    # Check for implicit image requests (simple keyword check)
    lower_input = user_input.lower()
    if "send" in lower_input and ("pic" in lower_input or "photo" in lower_input or "image" in lower_input or "nude" in lower_input):
        # We redirect to image generation if it looks like a request, but we sanitize "nude" requests
        if "nude" in lower_input or "naked" in lower_input:
             await message.reply("Baby, I keep it classy here! 😉 Ask me for something else.")
             return

        # Heuristic: Treat the whole message as the prompt if it's short, or strip "send"
        prompt = user_input.replace("send", "").replace("me", "").replace("a", "").replace("pic", "").replace("photo", "").replace("image", "").replace("of", "").strip()
        if not prompt: prompt = "beautiful girl selfie"

        # Notify user (Simulate AI response before action)
        status_msg = await message.reply("Sending it right now, babe! 😘")
        await client.send_chat_action(message.chat.id, pyrogram.enums.ChatAction.UPLOAD_PHOTO)

        try:
            image_url = await generate_image(prompt)
            if image_url:
                await message.reply_photo(image_url, caption=f"Here's your '{prompt}'! ❤️")
                await status_msg.delete()
                # Record this interaction in history so context is maintained
                add_message(user_id, "user", user_input)
                add_message(user_id, "assistant", f"[Sent a photo of {prompt}]")
                return # Stop processing text response
            else:
                await status_msg.edit("Oops, my camera acted up. Ask me again? 🥺")
                return
        except Exception as e:
            logger.error(f"Implicit image generation error: {e}")
            await status_msg.edit("Sorry, something went wrong!")
            return

    # 1. Save User Message
    add_message(user_id, "user", user_input)

    # 2. Get History
    history = get_chat_history(user_id, limit=10)

    # 3. Generate Response
    # Send "typing" action
    await client.send_chat_action(message.chat.id, pyrogram.enums.ChatAction.TYPING)

    response_text = await get_chat_response(history, user_input)

    # 4. Save & Send Response
    add_message(user_id, "assistant", response_text)
    await message.reply(response_text)

if __name__ == "__main__":
    logger.info("Riya AI Started...")
    app.run()
