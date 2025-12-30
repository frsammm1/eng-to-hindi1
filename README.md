# Telegram Content Transfer Bot (Dual Mode)
**A professional tool to copy content from any Telegram channel (including Private/Restricted) to a destination channel.**

## Architecture
This bot uses a **Dual-Client System**:
1.  **The Bot:** (Requires `BOT_TOKEN`) - Acts as the interface. You send commands (`/start`, `/batch`) to it.
2.  **The Userbot:** (Requires Login) - Acts as the worker. It performs the actual message copying. This allows it to access private channels that you (the user) have joined.

## Features
- **Access Private Channels:** Copies content from restricted/private channels via Userbot.
- **High Fidelity:** Preserves files, media, captions, and formatting.
- **Range Selection:** Specify Start and End Message IDs.
- **Robust:** Handles Rate Limits (`FloodWait`) automatically.
- **Live Status:** Updates speed, ETA, and progress every 5 seconds.

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
    Create a `.env` file:
    ```
    API_ID=123456
    API_HASH=abcdef123456...
    BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    MONGO_URI=mongodb+srv://...

    # Optional
    OWNER_ID=123456789 (Your User ID to restrict access)
    ```

## First Run & Login

1.  Run the script:
    ```bash
    python main.py
    ```
2.  **Bot Start:** The script will first start the Bot.
3.  **Userbot Login:** The terminal will prompt:
    > "Enter phone number:"

    Enter your phone number (e.g., `+919999999999`).
4.  Enter the **OTP** you receive on Telegram.
5.  (If 2FA is on) Enter your password.
6.  **Success:** You will see "Service is Ready. Idling...". The session is saved to `my_userbot.session`.

## Usage

**Start:**
Open your Bot in Telegram and send `/start`.

**Start Transfer:**
```
/batch <Source_ID> <Dest_ID> <Start_Msg_ID> <End_Msg_ID>
```
*   **Source_ID:** ID of the channel to copy FROM. (Can be a private channel ID like `-100xxxx` if the Userbot is a member).
*   **Dest_ID:** ID of the channel to copy TO.
*   **IDs:** The Message IDs to start and end at.

**Example:**
```
/batch -1001111111111 -1002222222222 100 500
```

**Cancel:**
```
/cancel
```

**Status:**
```
/status
```

## Important Notes
- **Permissions:**
    - The **Userbot** must be a member of the **Source Channel**.
    - The **Userbot** (or Bot) must have write access to the **Destination Channel**.
- **Privacy:** Your session file (`my_userbot.session`) grants full access to your account. Keep it safe.
