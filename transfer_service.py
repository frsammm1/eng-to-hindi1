import asyncio
import logging
import time
from pyrogram import Client, errors
from database import update_job_progress, complete_job, get_active_job

logger = logging.getLogger(__name__)

class TransferEngine:
    def __init__(self, bot: Client, userbot: Client):
        self.bot = bot         # Bot client for UI/Status updates
        self.userbot = userbot # Userbot client for Copying
        self.active_tasks = {}

    async def start_transfer(self, job):
        user_id = job['user_id']
        if user_id in self.active_tasks:
            self.active_tasks[user_id].cancel()

        task = asyncio.create_task(self._process_transfer(job))
        self.active_tasks[user_id] = task
        return task

    async def stop_transfer(self, user_id):
        if user_id in self.active_tasks:
            self.active_tasks[user_id].cancel()
            del self.active_tasks[user_id]
            return True
        return False

    async def _process_transfer(self, job):
        source = job['source']
        dest = job['dest']
        start_id = job['current_id']
        end_id = job['end_id']
        job_id = job['_id']
        user_id = job['user_id']

        logger.info(f"Starting transfer job {job_id}: {source} -> {dest} ({start_id}-{end_id})")

        total = job['total_count']
        processed = job['processed']
        start_time = time.time()

        # Speed tracking
        total_bytes = 0

        last_update_time = 0
        status_msg = None

        # Initial Status via Bot
        try:
            status_msg = await self.bot.send_message(
                chat_id=user_id,
                text=f"🚀 **Transfer Started**\n\nSource: `{source}`\nDest: `{dest}`\nRange: `{start_id}` - `{end_id}`"
            )
        except Exception as e:
            logger.error(f"Could not send status message to user {user_id}: {e}")

        try:
            for msg_id in range(start_id, end_id + 1):
                current_job_status = get_active_job(job['user_id'])
                if not current_job_status:
                    logger.info("Job cancelled via DB check.")
                    break

                # Copy Message with Retry Loop
                while True:
                    try:
                        msg = await self.userbot.copy_message(
                            chat_id=dest,
                            from_chat_id=source,
                            message_id=msg_id
                        )

                        # Track size if media/file
                        if msg:
                            if msg.document: total_bytes += msg.document.file_size
                            elif msg.video: total_bytes += msg.video.file_size
                            elif msg.photo: total_bytes += msg.photo.file_size
                            elif msg.audio: total_bytes += msg.audio.file_size

                        success = True
                        await asyncio.sleep(0.5) # Rate limit courtesy
                        break # Success, exit retry loop

                    except errors.FloodWait as e:
                        logger.warning(f"FloodWait: Sleeping {e.value} seconds...")
                        if status_msg:
                            try:
                                await status_msg.edit(f"⚠️ FloodWait hit. Sleeping for {e.value}s...")
                            except Exception:
                                pass
                        await asyncio.sleep(e.value)
                        # Loop continues to retry

                    except errors.MessageEmpty:
                        success = False
                        break # Cannot retry empty message
                    except errors.MessageIdInvalid:
                        success = False
                        break # Cannot retry invalid ID
                    except Exception as e:
                        logger.error(f"Error copying {msg_id}: {e}")
                        success = False
                        break # Unknown error, skip to next message

                update_job_progress(job_id, msg_id, success)
                processed += 1

                # Update Status (Every 5s)
                if time.time() - last_update_time > 5 and status_msg:
                    elapsed = time.time() - start_time
                    speed_msgs = processed / elapsed if elapsed > 0 else 0

                    # Calculate MB/s
                    mb_transferred = total_bytes / (1024 * 1024)
                    speed_mb = mb_transferred / elapsed if elapsed > 0 else 0

                    percent = ((msg_id - job['start_id'] + 1) / total) * 100
                    remaining = total - (msg_id - job['start_id'] + 1)
                    eta = remaining / speed_msgs if speed_msgs > 0 else 0

                    text = (
                        f"📊 **Transfer Progress**\n\n"
                        f"✅ Processed: `{msg_id - job['start_id'] + 1}` / `{total}`\n"
                        f"📈 Progress: `{percent:.2f}%`\n"
                        f"⚡ Speed: `{speed_msgs:.1f} msg/s` | `{speed_mb:.2f} MB/s`\n"
                        f"⏳ ETA: `{int(eta)}s`\n\n"
                        f"Current ID: `{msg_id}`"
                    )
                    try:
                        await status_msg.edit(text)
                        last_update_time = time.time()
                    except Exception:
                        pass

            complete_job(job_id)
            if status_msg:
                await status_msg.edit(
                    f"✅ **Transfer Completed!**\n\n"
                    f"Total Processed: `{processed}`\n"
                    f"Total Data: `{total_bytes / (1024*1024):.2f} MB`"
                )

        except asyncio.CancelledError:
            if status_msg: await status_msg.edit("🛑 **Transfer Cancelled.**")
            raise
        except Exception as e:
            if status_msg: await status_msg.edit(f"❌ **Error:** {str(e)}")
        finally:
            if job['user_id'] in self.active_tasks:
                del self.active_tasks[job['user_id']]
