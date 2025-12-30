# Telegram Smart Cloner (Userbot)
**A powerful Userbot to clone content from ANY channel (Private/Public) to your own.**

## Features
- **Userbot Mode Only:** Runs on your account, giving it access to everything you see.
- **Smart Parsing:** Auto-detects Chat IDs and Message IDs from links (Private, Public, Topics).
- **Clone Wizard:** Simple `/clone` command walks you through setup.
- **High Speed:** Tracks Speed (MB/s), ETA, and Progress.
- **Content Fidelity:** Copies files, media, captions exactly as they are.

## Setup

1.  **Clone & Install:**
    ```bash
    git clone <repo_url>
    pip install -r requirements.txt
    ```

2.  **Config:**
    Create a `.env` file:
    ```
    API_ID=123456
    API_HASH=abcdef...
    MONGO_URI=mongodb+srv://...
    ```
    *(Note: No BOT_TOKEN needed)*

3.  **Run & Login:**
    ```bash
    python main.py
    ```
    - Enter Phone Number & OTP when prompted.
    - Session saved to `my_userbot.session`.

## Usage

**1. Start the Wizard:**
Send `/clone` to **Saved Messages** (or any chat).

**2. Provide First Link:**
Copy the link of the **First Message** from the source channel (Private or Public) and send it.
> *Example: `https://t.me/c/1234567890/100`*

**3. Provide Last Link:**
Copy the link of the **Last Message** and send it.

**4. Provide Destination ID:**
Send the Chat ID of your target channel (e.g., `-100987654321`).
> *Tip: Use the `/id` command inside your target channel to get its ID.*

**5. Start:**
Type `start` to begin the transfer.

## Commands
- `/clone` - Start setup.
- `/cancel` - Stop current job or setup.
- `/status` - View live progress (Speed, ETA).
- `/id` - Get current chat ID.

## Notes
- **Private Channels:** Since this is a Userbot, if YOU can see the channel, the Bot can copy from it.
- **Permissions:** You must have permission to post in the Destination Channel.
