import re
import logging

logger = logging.getLogger(__name__)

def parse_message_link(link):
    """
    Parses a Telegram message link to extract Chat ID and Message ID.
    Supports:
    - Public: https://t.me/username/123
    - Private: https://t.me/c/1234567890/123
    - Topic: https://t.me/c/1234567890/123/456 (Thread ID ignored for now, just gets Msg ID)

    Returns:
        (chat_id, message_id) or None if invalid.
        Note: Private chat IDs returned as -100... integer format.
    """
    link = link.strip()

    # Regex for Private Channels/Groups: t.me/c/{channel_id}/{msg_id} or .../{thread_id}/{msg_id}
    # We grab the last number as msg_id, and the one after /c/ as chat_id
    private_pattern = r"t\.me/c/(\d+)/(\d+)(?:/(\d+))?"

    # Regex for Public Channels/Groups: t.me/{username}/{msg_id}
    public_pattern = r"t\.me/([a-zA-Z0-9_]+)/(\d+)$"

    # Check Private first
    match = re.search(private_pattern, link)
    if match:
        channel_id_str = match.group(1)
        # If there are 3 groups and the 3rd is present, it's likely Topic ID / Msg ID logic.
        # Standard: t.me/c/ID/MSG
        # Topic: t.me/c/ID/THREAD/MSG

        # Actually, pyrogram/client behavior:
        # If 3 parts: group(2) is thread_id, group(3) is msg_id
        # If 2 parts: group(2) is msg_id, group(3) is None

        msg_id = match.group(2)
        potential_thread_or_msg = match.group(3)

        if potential_thread_or_msg:
             # It was t.me/c/ID/THREAD/MSG
             msg_id = potential_thread_or_msg

        # Private Chat IDs in links usually need -100 prefix when used via API
        chat_id = int(f"-100{channel_id_str}")
        return chat_id, int(msg_id)

    # Check Public
    match = re.search(public_pattern, link)
    if match:
        username = match.group(1)
        msg_id = match.group(2)
        # Return username as chat_id (Pyrogram resolves it)
        return username, int(msg_id)

    return None
