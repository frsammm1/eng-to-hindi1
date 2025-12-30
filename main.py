import logging
import asyncio
from pyrogram import Client, filters, idle
from config import Config
from database import check_connection, create_job, cancel_job, get_active_job
from transfer_service import TransferEngine
from utils import parse_message_link

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Validate Config
Config.validate()

if not check_connection():
    exit(1)

# Initialize Single Userbot Client
app = Client(
    "my_userbot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)

engine = TransferEngine(app)

# --- Conversation State Management ---
# Map user_id -> {step: 'wait_start_link'|'wait_end_link'|'wait_dest', data: {...}}
user_states = {}

@app.on_message(filters.command("start") & filters.me)
async def start_command(client, message):
    text = (
        "🚀 **Telegram Smart Cloner (Userbot)**\n\n"
        "I am running on your account. I can copy content from any channel you can access.\n\n"
        "**Usage:**\n"
        "1. Send `/clone` to start the wizard.\n"
        "2. Provide the Link of the **First Message**.\n"
        "3. Provide the Link of the **Last Message**.\n"
        "4. Provide the **Destination Channel ID**.\n"
        "5. Type `start` to begin.\n\n"
        "**Other Commands:**\n"
        "`/cancel` - Stop current job.\n"
        "`/status` - Check progress."
    )
    await message.edit(text)

@app.on_message(filters.command("clone") & filters.me)
async def clone_command(client, message):
    if get_active_job(message.from_user.id):
        await message.reply("⚠️ Active job exists. Use `/cancel` first.")
        return

    user_states[message.from_user.id] = {"step": "wait_start_link", "data": {}}
    await message.reply("🔗 **Step 1:** Send the **Link** of the **First Message** you want to copy.")

@app.on_message(filters.command("cancel") & filters.me)
async def cancel_command(client, message):
    if message.from_user.id in user_states:
        del user_states[message.from_user.id]
        await message.reply("❌ Setup cancelled.")
        return

    stopped = await engine.stop_transfer(message.from_user.id)
    cancel_job(message.from_user.id)

    if stopped:
        await message.reply("✅ Job stopped.")
    else:
        await message.reply("⚠️ No active job.")

@app.on_message(filters.command("status") & filters.me)
async def status_command(client, message):
    job = get_active_job(message.from_user.id)
    if not job:
        await message.reply("💤 No active job.")
        return
    await message.reply(f"🔄 **Processing:** {job['current_id']} / {job['end_id']}")

@app.on_message(filters.text & filters.me & ~filters.command(["start", "clone", "cancel", "status", "id"]))
async def conversation_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return

    state = user_states[user_id]
    step = state["step"]
    text = message.text.strip()

    # Step 1: Wait for Start Link
    if step == "wait_start_link":
        result = parse_message_link(text)
        if not result:
            await message.reply("❌ Invalid Link. Please send a valid Telegram message link.")
            return

        state["data"]["source_chat"] = result[0]
        state["data"]["start_id"] = result[1]
        state["step"] = "wait_end_link"

        await message.reply(
            f"✅ **Start Point Set:** Chat `{result[0]}`, Msg `{result[1]}`\n\n"
            "🔗 **Step 2:** Send the **Link** of the **Last Message**."
        )

    # Step 2: Wait for End Link
    elif step == "wait_end_link":
        result = parse_message_link(text)
        if not result:
            await message.reply("❌ Invalid Link.")
            return

        # Validation: Must be same chat
        if result[0] != state["data"]["source_chat"]:
            await message.reply("❌ **Error:** Start and End links must be from the **same chat**.")
            return

        state["data"]["end_id"] = result[1]

        # Ensure Start < End
        if state["data"]["start_id"] > state["data"]["end_id"]:
            state["data"]["start_id"], state["data"]["end_id"] = state["data"]["end_id"], state["data"]["start_id"]

        state["step"] = "wait_dest"

        await message.reply(
            f"✅ **Range Set:** `{state['data']['start_id']}` to `{state['data']['end_id']}`\n\n"
            "🎯 **Step 3:** Send the **Destination Channel ID** (e.g., `-100xxxx`).\n"
            "*(Tip: Use `/id` in the target channel to find it if I'm admin there)*"
        )

    # Step 3: Wait for Dest ID
    elif step == "wait_dest":
        try:
            dest_id = int(text)
            state["data"]["dest_chat"] = dest_id
            state["step"] = "confirm"

            await message.reply(
                "📝 **Summary:**\n"
                f"Source: `{state['data']['source_chat']}`\n"
                f"Dest: `{dest_id}`\n"
                f"Range: `{state['data']['start_id']}` - `{state['data']['end_id']}`\n\n"
                "🚀 Type **start** to begin."
            )
        except ValueError:
            await message.reply("❌ Invalid ID. Please send a numeric Chat ID (e.g. -100123456).")

    # Step 4: Confirm Start
    elif step == "confirm":
        if text.lower() == "start":
            # Create Job
            data = state["data"]
            job_id = create_job(user_id, data["source_chat"], data["dest_chat"], data["start_id"], data["end_id"])

            if job_id:
                del user_states[user_id]
                job = get_active_job(user_id)
                await message.reply("✅ Job Created. Starting Transfer...")
                await engine.start_transfer(job)
            else:
                await message.reply("❌ Error creating job.")
        else:
            await message.reply("❌ Type `start` to confirm or `/cancel` to abort.")

@app.on_message(filters.command("id") & filters.me)
async def id_command(client, message):
    await message.reply(f"Chat ID: `{message.chat.id}`")

if __name__ == "__main__":
    logger.info("Starting Userbot...")
    app.run()
