import logging
import asyncio
from pyrogram import Client, filters, idle
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

# --- Initialize Clients ---

# 1. Bot Client (Interface)
bot = Client(
    "ssc_transfer_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# 2. User Client (Worker)
# This will trigger interactive login if 'my_userbot.session' is missing
userbot = Client(
    "my_userbot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)

# Initialize Engine with BOTH clients
engine = TransferEngine(bot_client=bot, user_client=userbot)

# --- Bot Commands ---

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    text = (
        "🚀 **Telegram Content Transfer Bot**\n\n"
        "I am the Control Interface. The **Userbot** (Worker) will handle the actual copying.\n\n"
        "**Features:**\n"
        "• Copy from Private Channels (Userbot access)\n"
        "• Preserve Files, Media, Text\n"
        "• Range Selection\n\n"
        "**Commands:**\n"
        "`/batch <source> <dest> <start_id> <end_id>`\n"
        "`/cancel`\n"
        "`/status`\n\n"
        "**Note:** Use channel IDs (e.g., `-100xxxx`). Ensure the Userbot account has joined the source."
    )
    await message.reply(text)

@bot.on_message(filters.command("batch"))
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

@bot.on_message(filters.command("cancel"))
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

@bot.on_message(filters.command("status"))
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

async def main():
    logger.info("Starting Bot Client...")
    await bot.start()

    logger.info("Starting Userbot Client (CLI Login may be required)...")
    await userbot.start()

    me = await userbot.get_me()
    logger.info(f"Userbot Started as: {me.first_name} (ID: {me.id})")

    bot_info = await bot.get_me()
    logger.info(f"Bot Started as: @{bot_info.username}")

    logger.info("Service is Ready. Idling...")
    await idle()

    await bot.stop()
    await userbot.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
