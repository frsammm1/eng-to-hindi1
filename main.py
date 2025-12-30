import os
import asyncio
import logging
import time
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, MessageNotModified
from config import Config
from pdf_handler import extract_and_store, rebuild_final_pdf
from database import (
    check_connection, reset_file_tasks, get_pending_tasks,
    update_task_status, get_task_counts
)
from translator import translate_text

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validate Config
Config.validate()

# Check Database Connection
if not check_connection():
    logger.error("❌ Critical: MongoDB connection failed. Exiting...")
    exit(1)

app = Client(
    "ssc_heavy_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# --- Process Manager ---
class ProcessManager:
    """Manages the lifecycle of a file processing request."""
    def __init__(self, file_id, chat_id, message_id):
        self.file_id = file_id
        self.chat_id = chat_id
        self.message_id = message_id
        self.start_time = time.time()
        self.status = "Initializing"
        self.is_running = True
        self.semaphore = asyncio.Semaphore(10) # Limit concurrent translations

    async def run(self, input_path):
        try:
            # 1. Extraction
            self.status = "Extracting Text"
            logger.info(f"[{self.file_id}] Starting Extraction")
            reset_file_tasks(self.file_id) # Clean old run

            # Run blocking extraction in thread
            success = await asyncio.to_thread(extract_and_store, input_path, self.file_id)
            if not success:
                raise Exception("Extraction failed")

            # 2. Translation
            self.status = "Translating"
            logger.info(f"[{self.file_id}] Starting Translation")

            # Fetch all pending tasks
            tasks = await asyncio.to_thread(get_pending_tasks, self.file_id)
            total_tasks = len(tasks)
            logger.info(f"[{self.file_id}] Found {total_tasks} text blocks to translate")

            # Create async workers
            # We process in chunks or all at once with semaphore?
            # Semaphore is better for rate limiting.
            worker_tasks = [self.process_single_task(t) for t in tasks]
            if worker_tasks:
                 await asyncio.gather(*worker_tasks)

            # 3. PDF Rebuild
            self.status = "Generating PDF"
            logger.info(f"[{self.file_id}] Rebuilding PDF")
            output_name = f"HINDI_SSC_{self.file_id[:8]}.pdf"
            output_path = await asyncio.to_thread(rebuild_final_pdf, self.file_id, input_path, output_name)

            return output_path

        except Exception as e:
            logger.error(f"[{self.file_id}] Process Error: {e}")
            self.status = f"Error: {str(e)}"
            return None
        finally:
            self.is_running = False

    async def cleanup(self):
        """Cleanup resources manually."""
        pass # Add more cleanup logic if needed

    async def process_single_task(self, task):
        async with self.semaphore:
            try:
                original = task.get('original_text')
                if not original: return

                # Call async translator
                hindi = await translate_text(original)
                if hindi:
                    # Update DB (non-blocking wrapper)
                    await asyncio.to_thread(update_task_status, task['_id'], hindi)
            except Exception as e:
                logger.error(f"Task error: {e}")

# Global Tracker
active_processes = {} # file_id -> ProcessManager

async def progress_monitor(client):
    """Background task to update progress every 12 seconds."""
    logger.info("Starting Progress Monitor")
    while True:
        try:
            # Iterate over a copy of keys to avoid runtime modification issues
            current_files = list(active_processes.keys())

            for file_id in current_files:
                pm = active_processes.get(file_id)
                if not pm: continue

                # Get DB counts
                total, completed = await asyncio.to_thread(get_task_counts, file_id)

                percent = 0
                if total > 0:
                    percent = (completed / total) * 100

                # Format time
                elapsed = int(time.time() - pm.start_time)

                text = (
                    f"⚙️ **Status:** {pm.status}\n"
                    f"📊 **Progress:** {completed}/{total} ({percent:.1f}%)\n"
                    f"⏱ **Time Elapsed:** {elapsed}s\n\n"
                    "Please wait..."
                )

                # Send Update
                try:
                    await client.edit_message_text(pm.chat_id, pm.message_id, text)
                except MessageNotModified:
                    pass
                except FloodWait as e:
                    logger.warning(f"FloodWait: {e.value}")
                    # Don't sleep here, just skip this update loop for this user
                except Exception as e:
                    logger.warning(f"Update failed for {file_id}: {e}")

                # Avoid overwriting "Complete" message if process finished recently
                if not pm.is_running and pm.status != "Generating PDF":
                    # If it's not running and status isn't the last active status, skip update
                    pass

            await asyncio.sleep(12) # Strict 12s interval
        except Exception as e:
            logger.error(f"Monitor Loop Error: {e}")
            await asyncio.sleep(12)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply(
        "👋 **Welcome to the Advanced SSC Translator Bot!**\n\n"
        "✅ **Features:**\n"
        "- Asynchronous Processing\n"
        "- Real-time Progress Updates\n"
        "- AI-Powered Translation (English -> Hindi)\n\n"
        "📂 **How to use:**\n"
        "Simply send me a PDF file to begin."
    )

@app.on_message(filters.document & filters.private)
async def handle_document(client, message):
    file_id = message.document.file_unique_id

    if file_id in active_processes and active_processes[file_id].is_running:
        await message.reply("⚠️ This file is already being processed!")
        return

    msg = await message.reply("🚀 **Initializing...**")

    # Start Manager
    pm = ProcessManager(file_id, message.chat.id, msg.id)
    active_processes[file_id] = pm

    try:
        # Download
        pm.status = "Downloading PDF"
        doc_path = await message.download()
        
        # Run
        output_path = await pm.run(doc_path)
        
        # Result
        if output_path and os.path.exists(output_path):
            # Final Status Update - Mark as done so monitor doesn't overwrite
            pm.is_running = False

            await client.edit_message_text(message.chat.id, msg.id, "✅ **Translation Complete!** Uploading...")
            await message.reply_document(
                output_path,
                caption=f"🎉 **Translated File:** {message.document.file_name}\nPowered by SSC Bot"
            )
        else:
            await client.edit_message_text(message.chat.id, msg.id, f"❌ **Failed:** {pm.status}")

    except Exception as e:
        logger.error(f"Handler Error: {e}")
        await client.edit_message_text(message.chat.id, msg.id, f"❌ **Error:** {str(e)}")
    finally:
        # Cleanup
        if 'doc_path' in locals() and os.path.exists(doc_path):
            os.remove(doc_path)
        if 'output_path' in locals() and output_path and os.path.exists(output_path):
            os.remove(output_path)

        active_processes.pop(file_id, None)

if __name__ == "__main__":
    logger.info("Bot Starting...")
    # Start the monitor loop
    # Since app.run() blocks, we need to schedule the monitor before,
    # OR use app.start(), monitor(), app.stop() manually?
    # Pyrogram app.run() is convenient. We can add the monitor as a task in `start` callback?
    # Or just use `loop.create_task` before `app.run()`.

    loop = asyncio.get_event_loop()
    loop.create_task(progress_monitor(app))

    app.run()
