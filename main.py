import os
import asyncio
import logging
import time
from pyrogram import Client, filters
from config import Config
from pdf_handler import extract_and_store, rebuild_final_pdf, create_mini_pdf
from database import get_next_batch, update_task, get_completed_count, get_total_count, check_connection
from translator import translate_with_retry

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
    "ssc_heavy_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# Shared state for progress tracking
class ProgressState:
    def __init__(self):
        self.state = "Idle" # Idle, Extracting, Translating, Generating
        self.total_tasks = 0
        self.completed_tasks = 0
        self.is_processing = False

progress_tracker = {} # file_id -> ProgressState

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply(
        "Welcome to the SSC Translation Bot! 🇮🇳\n\n"
        "Send me a PDF file (e.g., Previous Year Questions) and I will translate it into Hindi.\n"
        "I will keep you updated on the progress.\n\n"
        "**Note:** Please be patient as translation takes time."
    )

async def update_progress_message(client, chat_id, message_id, file_id):
    """Updates the status message every 15 seconds."""
    last_text = ""
    while True:
        if file_id not in progress_tracker:
            break

        state = progress_tracker[file_id]
        if not state.is_processing:
            break

        # Calculate percentage
        percent = 0
        if state.total_tasks > 0:
            percent = (state.completed_tasks / state.total_tasks) * 100

        text = (
            f"⚙️ **Status:** {state.state}\n"
            f"📊 **Progress:** {state.completed_tasks}/{state.total_tasks} ({percent:.1f}%)\n"
            "⏳ Working..."
        )

        if text != last_text:
            try:
                await client.edit_message_text(chat_id, message_id, text)
                last_text = text
            except Exception as e:
                logger.warning(f"Failed to update message: {e}")

        await asyncio.sleep(15)

@app.on_message(filters.document & filters.private)
async def start_process(client, message):
    file_id = message.document.file_unique_id

    if file_id in progress_tracker and progress_tracker[file_id].is_processing:
        await message.reply("⚠️ This file is already being processed.")
        return

    status_msg = await message.reply("🚀 **Starting Process...**\n\n⬇️ Downloading PDF...")
    doc_path = await message.download()
    
    # Initialize State
    state = ProgressState()
    state.is_processing = True
    state.state = "Extracting Text"
    progress_tracker[file_id] = state

    # Start Progress Monitor
    monitor_task = asyncio.create_task(update_progress_message(client, message.chat.id, status_msg.id, file_id))

    try:
        # 1. Extraction (Run in thread)
        logger.info(f"Starting extraction for {file_id}")
        await asyncio.to_thread(extract_and_store, doc_path, file_id)

        # Update Total Count
        state.total_tasks = await asyncio.to_thread(get_total_count, file_id)
        state.state = "Translating"
        
        # 2. Translation Loop
        processed_in_session = 0
        while True:
            batch = await asyncio.to_thread(get_next_batch, file_id)
            if not batch:
                break

            # Update counts from DB to be accurate (or just increment local)
            state.completed_tasks = await asyncio.to_thread(get_completed_count, file_id)
            
            # Process batch
            for task in batch:
                hindi = await asyncio.to_thread(translate_with_retry, task['original_text'])
                if hindi:
                    await asyncio.to_thread(update_task, task['_id'], hindi)
                    processed_in_session += 1
                    state.completed_tasks += 1

            # Mini PDF every 100 questions (Optional, maybe skip to save API/Time)
            # User asked for improvements, maybe sending mini PDFs is good but slows down.
            # I will keep it but make it non-blocking
            if processed_in_session > 0 and processed_in_session % 100 == 0:
                 mini_name = f"batch_{processed_in_session}_{file_id[:5]}.pdf"
                 await asyncio.to_thread(create_mini_pdf, file_id, mini_name)
                 if os.path.exists(mini_name):
                     try:
                        await message.reply_document(mini_name, caption=f"✅ {processed_in_session} questions done!")
                        os.remove(mini_name)
                     except Exception as e:
                        logger.error(f"Failed to send mini pdf: {e}")

            # Small sleep not needed if we are in a loop in async handler, but good to yield
            await asyncio.sleep(0.1)

        # 3. Final PDF
        state.state = "Generating Final PDF"
        final_name = f"HINDI_{message.document.file_name}"
        output_path = await asyncio.to_thread(rebuild_final_pdf, file_id, doc_path, final_name)
        
        # Stop Monitor
        state.is_processing = False
        progress_tracker.pop(file_id, None)
        await monitor_task # Wait for last update or cancel?
        # Actually better to cancel monitor and send final update
        monitor_task.cancel()

        if output_path and os.path.exists(output_path):
            await client.edit_message_text(message.chat.id, status_msg.id, "✅ **Translation Complete!** Sending file...")
            await message.reply_document(output_path, caption="Jai Hind! 🇮🇳 Poori book Hindi mein tayyar hai.")
            os.remove(output_path)
        else:
            await client.edit_message_text(message.chat.id, status_msg.id, "❌ **Error:** Failed to generate final PDF.")

    except Exception as e:
        logger.error(f"Error in process: {e}")
        state.is_processing = False
        progress_tracker.pop(file_id, None)
        monitor_task.cancel()
        await client.edit_message_text(message.chat.id, status_msg.id, f"❌ **Error:** {str(e)}")

    finally:
        if os.path.exists(doc_path):
            os.remove(doc_path)

if __name__ == "__main__":
    logger.info("Bot Started...")
    app.run()
