# Telegram Content Transfer Bot
**A robust tool to copy messages (text, media, files) from one channel to another sequentially.**

## Features
- **High Speed:** Copies messages one by one to ensure order.
- **Resume Capability:** Tracks progress so you can stop and resume.
- **Robustness:** Handles FloodWait (rate limits) automatically.
- **Media Support:** Transfers all file types, images, videos, and captions.
- **Status Updates:** Live progress updates every 5 seconds.
- **Userbot Mode:** Supports login via phone number to access private channels.

## Setup

1.  **Clone the Repo:**
    ```bash
    git clone <repo_url>
    cd <repo_folder>
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Variables:**
    Create a `.env` file or set variables in your environment:
    ```
    API_ID=123456
    API_HASH=abcdef123456...
    MONGO_URI=mongodb+srv://...

    # Optional: Leave empty to login with phone number
    BOT_TOKEN=
    ```

## How to Login (Userbot Mode)

To access **Private Channels** or act as a user:

1.  Ensure `BOT_TOKEN` is empty or removed from `.env`.
2.  Run the bot:
    ```bash
    python main.py
    ```
3.  The terminal will ask for your **Phone Number**. Enter it (e.g., `+919999999999`).
4.  Enter the **OTP** sent to your Telegram app.
5.  If you have 2FA enabled, enter your password.
6.  Once logged in, the session is saved to `my_userbot.session`. You won't need to login again.

## Usage

**Start the Bot:**
Send `/start` to the bot (saved messages or any chat if running as Userbot).

**Batch Transfer:**
```
/batch <Source_ID> <Dest_ID> <Start_Msg_ID> <End_Msg_ID>
```
*   **Source_ID:** ID of the channel to copy from (e.g., `-1001234567890`).
*   **Dest_ID:** ID of the channel to send to.
*   **Start_Msg_ID:** The ID of the first message to copy.
*   **End_Msg_ID:** The ID of the last message to copy.

**Example:**
```
/batch -1001111111111 -1002222222222 100 500
```

**Cancel Transfer:**
```
/cancel
```

**Check Status:**
```
/status
```

## Important Notes
- **Permissions:** If using Bot Mode (`BOT_TOKEN`), the bot must be an Admin in the destination channel and a member of the source channel.
- **Private Channels:** You must use **Userbot Mode** (Login) to copy from private channels you have joined.
- **Speed:** The bot adds a small delay to avoid bans, but FloodWait sleep is automatic.
