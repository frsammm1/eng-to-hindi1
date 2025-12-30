import logging
import asyncio
from pyrogram import Client, filters, idle, errors
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

# --- Clients ---
bot = Client(
    "ssc_transfer_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

userbot = Client(
    "my_userbot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)

userbot_active = False

# --- State Management ---
# user_id -> {step: str, data: dict}
user_states = {}

# --- Engine ---
engine = TransferEngine(bot_client=bot, user_client=userbot)

# --- Helper: Conversation Reset ---
def reset_state(user_id):
    if user_id in user_states:
        del user_states[user_id]

# --- Bot Commands ---

@bot.on_message(filters.command("start"))
async def start_command(client, message):
    status = "🟢 Online" if userbot_active else "🔴 Offline (Login Required)"
    text = (
        "🚀 **Telegram Smart Cloner (Dual Mode)**\n\n"
        f"**Userbot Status:** {status}\n\n"
        "**Commands:**\n"
        "`/login` - Login to Userbot (Required for private channels).\n"
        "`/clone` - Start a Transfer Job.\n"
        "`/cancel` - Cancel current action.\n"
        "`/status` - Check Job Status."
    )
    await message.reply(text)

@bot.on_message(filters.command("login"))
async def login_command(client, message):
    global userbot_active
    if userbot_active:
        await message.reply("✅ Userbot is already logged in and active.")
        return

    user_states[message.from_user.id] = {"step": "auth_phone", "data": {}}
    await message.reply("📱 **Login Step 1:**\n\nPlease enter your **Phone Number** (with country code, e.g., `+919999999999`).")

@bot.on_message(filters.command("clone"))
async def clone_command(client, message):
    if not userbot_active:
        await message.reply("❌ **Userbot Offline.**\nPlease use `/login` first to enable cloning capabilities.")
        return

    if get_active_job(message.from_user.id):
        await message.reply("⚠️ You have an active job. Use `/status` or `/cancel`.")
        return

    user_states[message.from_user.id] = {"step": "clone_start_link", "data": {}}
    await message.reply("🔗 **Clone Setup:**\n\nSend the **Link** of the **First Message** (Start Point).")

@bot.on_message(filters.command("cancel"))
async def cancel_command(client, message):
    user_id = message.from_user.id

    # Cancel Conversation
    if user_id in user_states:
        reset_state(user_id)
        await message.reply("❌ Setup/Login cancelled.")
        return

    # Cancel Job
    if userbot_active:
        stopped = await engine.stop_transfer(user_id)
        cancel_job(user_id)
        if stopped:
            await message.reply("✅ Transfer Job Stopped.")
        else:
            await message.reply("⚠️ No active job found.")
    else:
        await message.reply("⚠️ Userbot is offline.")

@bot.on_message(filters.command("status"))
async def status_command(client, message):
    job = get_active_job(message.from_user.id)
    if not job:
        await message.reply("💤 No active job.")
        return
    await message.reply(
        f"🔄 **Job Status:**\n"
        f"Processed: `{job['processed']}`\n"
        f"Range: `{job['current_id']}` / `{job['end_id']}`"
    )

@bot.on_message(filters.text & ~filters.command(["start", "login", "clone", "cancel", "status"]))
async def conversation_handler(client, message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return

    state = user_states[user_id]
    step = state["step"]
    text = message.text.strip()
    data = state["data"]

    # --- Auth Flow ---
    if step == "auth_phone":
        try:
            await message.reply("⏳ Connecting...")
            await userbot.connect()
            sent_code = await userbot.send_code(text)

            data["phone"] = text
            data["phone_hash"] = sent_code.phone_code_hash
            state["step"] = "auth_otp"

            await message.reply(
                "📩 **OTP Sent!**\n\n"
                "Check your Telegram Service Notifications.\n"
                "Enter the OTP here (e.g., `1 2 3 4 5`)."
            )
        except Exception as e:
            await message.reply(f"❌ Error: {e}\nTry `/login` again.")
            await userbot.disconnect()
            reset_state(user_id)

    elif step == "auth_otp":
        try:
            phone = data["phone"]
            hash_ = data["phone_hash"]
            # Remove spaces if user sent "1 2 3 4 5"
            otp = text.replace(" ", "")

            await userbot.sign_in(phone, hash_, otp)

            # Login Success
            await message.reply("✅ **Login Successful!**\nUserbot is starting...")
            await userbot.disconnect() # Disconnect temp session
            await userbot.start()      # Start permanently

            global userbot_active
            userbot_active = True
            reset_state(user_id)

            me = await userbot.get_me()
            await message.reply(f"🤖 Userbot Active as: **{me.first_name}**")

        except errors.SessionPasswordNeeded:
            state["step"] = "auth_2fa"
            await message.reply("🔐 **2FA Enabled.**\nPlease enter your Two-Step Verification Password.")

        except Exception as e:
            await message.reply(f"❌ Login Failed: {e}")
            await userbot.disconnect()
            reset_state(user_id)

    elif step == "auth_2fa":
        try:
            await userbot.check_password(text)

            # Login Success
            await message.reply("✅ **Login Successful!**\nUserbot is starting...")
            await userbot.disconnect()
            await userbot.start()

            userbot_active = True
            reset_state(user_id)

            me = await userbot.get_me()
            await message.reply(f"🤖 Userbot Active as: **{me.first_name}**")

        except Exception as e:
            await message.reply(f"❌ Password Failed: {e}")
            await userbot.disconnect()
            reset_state(user_id)

    # --- Clone Wizard Flow ---
    elif step == "clone_start_link":
        result = parse_message_link(text)
        if not result:
            await message.reply("❌ Invalid Link.")
            return

        data["source_chat"] = result[0]
        data["start_id"] = result[1]
        state["step"] = "clone_end_link"

        await message.reply(f"✅ Start: `{result[1]}`\n\n🔗 **Next:** Send **End Message Link**.")

    elif step == "clone_end_link":
        result = parse_message_link(text)
        if not result:
            await message.reply("❌ Invalid Link.")
            return

        if result[0] != data["source_chat"]:
            await message.reply("❌ Chat mismatch! Links must be from the same chat.")
            return

        data["end_id"] = result[1]

        # Swap if needed
        if data["start_id"] > data["end_id"]:
            data["start_id"], data["end_id"] = data["end_id"], data["start_id"]

        state["step"] = "clone_dest"
        await message.reply(f"✅ Range: `{data['start_id']}` - `{data['end_id']}`\n\n🎯 **Next:** Send **Destination Channel ID**.")

    elif step == "clone_dest":
        try:
            dest_id = int(text)
            data["dest_chat"] = dest_id
            state["step"] = "clone_confirm"

            await message.reply(
                "📝 **Confirm Job:**\n"
                f"Source: `{data['source_chat']}`\n"
                f"Dest: `{dest_id}`\n"
                f"Range: `{data['start_id']}` - `{data['end_id']}`\n\n"
                "Type `start` to begin."
            )
        except ValueError:
            await message.reply("❌ Invalid ID.")

    elif step == "clone_confirm":
        if text.lower() == "start":
            user_id = message.from_user.id
            job_id = create_job(user_id, data["source_chat"], data["dest_chat"], data["start_id"], data["end_id"])

            if job_id:
                reset_state(user_id)
                job = get_active_job(user_id)
                await message.reply("🚀 **Job Started!**")
                await engine.start_transfer(job)
            else:
                await message.reply("❌ DB Error.")
        else:
            await message.reply("Type `start` or `/cancel`.")

async def main():
    logger.info("Starting Bot...")
    await bot.start()

    # Try starting Userbot
    global userbot_active
    try:
        logger.info("Attempting to start Userbot...")
        await userbot.start()
        userbot_active = True
        me = await userbot.get_me()
        logger.info(f"Userbot Started: {me.first_name}")
    except Exception as e:
        logger.warning(f"Userbot not logged in: {e}")
        userbot_active = False

    logger.info("Service Ready. Idling...")
    await idle()

    await bot.stop()
    if userbot_active:
        await userbot.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
