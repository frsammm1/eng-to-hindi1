import logging
import asyncio
from pyrogram import Client, filters
from config import Config
from database import check_connection, create_job, cancel_job, get_active_job
from transfer_service import TransferEngine

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

# Initialize Client
# Logic:
# 1. If BOT_TOKEN is present -> Start as Bot
# 2. If SESSION_STRING is present -> Start as Userbot (Memory)
# 3. Else -> Start as Userbot (File/Interactive Login)
if Config.BOT_TOKEN:
    logger.info("Starting in BOT mode (Bot Token provided).")
    app = Client(
        "ssc_transfer_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN
    )
elif Config.SESSION_STRING:
    logger.info("Starting in USERBOT mode (Session String provided).")
    app = Client(
        "ssc_transfer_userbot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        session_string=Config.SESSION_STRING
    )
else:
    logger.info("Starting in USERBOT mode (Interactive Login).")
    # This will check for 'my_userbot.session'.
    # If not found, it triggers CLI login.
    app = Client(
        "my_userbot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH
    )

# Initialize Transfer Engine
engine = TransferEngine(app)

@app.on_message(filters.command("start"))
async def start_command(client, message):
    text = (
        "🚀 **Telegram Content Transfer Bot**\n\n"
        "I can copy messages from one channel to another, one by one.\n"
        "I handle all file types, media, and text.\n\n"
        "**Commands:**\n"
        "`/batch <source> <dest> <start_id> <end_id>` - Start a transfer job.\n"
        "`/cancel` - Stop the current job.\n"
        "`/status` - Check current status.\n\n"
        "**Example:**\n"
        "`/batch -1001234567890 -1009876543210 100 500`\n\n"
        "**Note:** Ensure I am a member (or admin) in the source and destination channels."
    )
    await message.reply(text)

@app.on_message(filters.command("batch"))
async def batch_command(client, message):
    # Check permissions
    if Config.OWNER_ID and message.from_user.id != Config.OWNER_ID:
        await message.reply("❌ Access Denied. Only the owner can use this bot.")
        return

    # Check for active job
    if get_active_job(message.from_user.id):
        await message.reply("⚠️ You already have an active transfer job. Use `/cancel` first.")
        return

    # Parse arguments
    try:
        args = message.command
        if len(args) != 5:
            raise ValueError("Incorrect number of arguments")

        source = args[1]
        dest = args[2]
        start_id = int(args[3])
        end_id = int(args[4])

        # Convert IDs to int if they look like ints
        try:
            source = int(source)
        except: pass
        try:
            dest = int(dest)
        except: pass

    except Exception:
        await message.reply(
            "❌ **Usage Error**\n\n"
            "Format: `/batch <source_id> <dest_id> <start_id> <end_id>`\n"
            "Example: `/batch -1001234 -1005678 10 50`"
        )
        return

    # Create Job
    try:
        job_id = create_job(message.from_user.id, source, dest, start_id, end_id)
        if not job_id:
            await message.reply("❌ Database Error: Could not create job.")
            return

        # Fetch the full job object to pass to engine
        job = get_active_job(message.from_user.id)

        # Start Engine
        await engine.start_transfer(job)

    except Exception as e:
        logger.error(f"Error starting batch: {e}")
        await message.reply(f"❌ Error starting transfer: {e}")

@app.on_message(filters.command("cancel"))
async def cancel_command(client, message):
    if Config.OWNER_ID and message.from_user.id != Config.OWNER_ID:
        return

    user_id = message.from_user.id

    # Cancel in Engine
    stopped = await engine.stop_transfer(user_id)

    # Cancel in DB
    cancel_job(user_id)

    if stopped:
        await message.reply("✅ Job stopped and cancelled.")
    else:
        await message.reply("⚠️ No active job found to cancel.")

@app.on_message(filters.command("status"))
async def status_command(client, message):
    job = get_active_job(message.from_user.id)
    if not job:
        await message.reply("💤 No active transfers running.")
        return

    await message.reply(
        f"🔄 **Active Job:**\n"
        f"Source: `{job['source']}`\n"
        f"Dest: `{job['dest']}`\n"
        f"Current ID: `{job['current_id']}` / `{job['end_id']}`\n"
        f"Processed: `{job['processed']}`\n"
        f"Failed: `{job['failed']}`"
    )

if __name__ == "__main__":
    logger.info("Transfer Bot Service Started...")
    app.run()
