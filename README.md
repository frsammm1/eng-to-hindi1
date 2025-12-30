# Telegram Smart Cloner (Chat-Based)
**A Dual-Mode bot where you chat with the Bot to control the Userbot.**

## Architecture
1.  **Bot Interface:** You talk to `@YourBot` to send commands.
2.  **Userbot Worker:** The bot logs into your account (Userbot) to copy content from private/restricted channels.

## Setup
1.  **Deploy:**
    ```bash
    git clone <repo>
    pip install -r requirements.txt
    ```
2.  **Config (`.env`):**
    ```
    API_ID=12345
    API_HASH=abcdef...
    BOT_TOKEN=123456:ABC-DEF...
    MONGO_URI=mongodb+srv://...
    ```

3.  **Run:**
    ```bash
    python main.py
    ```

## How to Login (First Time)
1.  Start your bot in Telegram: `/start`.
    > It will say "Userbot Status: 🔴 Offline".
2.  Send `/login`.
3.  Enter your **Phone Number** (e.g., `+919999999999`).
4.  Enter the **OTP** code sent to your Telegram.
5.  (Optional) Enter **2FA Password** if enabled.
6.  The bot will confirm: "Userbot Active".

## How to Clone
1.  Send `/clone`.
2.  **Start Link:** Send the link of the first message to copy (e.g., `https://t.me/c/123/100`).
3.  **End Link:** Send the link of the last message.
4.  **Destination ID:** Send the Chat ID (e.g., `-100987...`).
5.  Type `start`.

## Commands
- `/login` - Log in to your User account via the Bot.
- `/clone` - Start a new copy job.
- `/cancel` - Stop jobs or setup.
- `/status` - Check progress (Speed, ETA).
