import os
import asyncio
import logging
import time
from pyrogram import Client, filters
from config import Config
from pdf_handler import extract_and_store, rebuild_final_pdf, create_mini_pdf
from database import get_next_batch, update_task, get_completed_count, get_total_count, check_connection, delete_file_tasks
from translator import translate_text

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

async def send_mini_pdf(client, message, file_id, mini_name):
    try:
        await asyncio.to_thread(create_mini_pdf, file_id, mini_name)
        if os.path.exists(mini_name):
            await message.reply_document(mini_name, caption=f"✅ Progress update!")
            os.remove(mini_name)
    except Exception as e:
        logger.error(f"Failed to send mini pdf: {e}")

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
        # 0. Cleanup old tasks
        await asyncio.to_thread(delete_file_tasks, file_id)

        # 1. Extraction (Run in thread)
        logger.info(f"Starting extraction for {file_id}")
        await asyncio.to_thread(extract_and_store, doc_path, file_id)

        # Update Total Count
        state.total_tasks = await asyncio.to_thread(get_total_count, file_id)
        state.state = "Translating"
        
        # 2. Translation Loop (Concurrent)
        processed_in_session = 0
        last_mini_pdf_sent_at = 0
        semaphore = asyncio.Semaphore(10) # Limit concurrent API calls to 10

        async def process_task(task):
            async with semaphore:
                hindi = await translate_text(task['original_text'])
                if hindi:
                    await asyncio.to_thread(update_task, task['_id'], hindi)
                    state.completed_tasks += 1
                    return True
                return False

        while True:
            # Fetch larger batch for concurrency
            batch = await asyncio.to_thread(get_next_batch, file_id, limit=50)
            if not batch:
                break

            # Process batch concurrently
            results = await asyncio.gather(*[process_task(task) for task in batch])
            processed_in_session += sum(1 for r in results if r)
            
            # Update counts from DB strictly occasionally
            if processed_in_session % 50 == 0:
                 state.completed_tasks = await asyncio.to_thread(get_completed_count, file_id)

            # Mini PDF every 200 questions (logic improved to handle batch jumps)
            if processed_in_session - last_mini_pdf_sent_at >= 200:
                 last_mini_pdf_sent_at = processed_in_session
                 mini_name = f"batch_{processed_in_session}_{file_id[:5]}.pdf"
                 asyncio.create_task(send_mini_pdf(client, message, file_id, mini_name)) # Fire and forget

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
