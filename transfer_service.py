import asyncio
import logging
import time
from pyrogram import Client, errors
from database import update_job_progress, complete_job, get_active_job

logger = logging.getLogger(__name__)

class TransferEngine:
    def __init__(self, bot_client: Client, user_client: Client):
        self.bot = bot_client   # For status updates
        self.user = user_client # For copying messages (access)
        self.active_tasks = {}  # Map user_id to asyncio.Task

    async def start_transfer(self, job):
        user_id = job['user_id']
        # Cancel existing task if any (double safety)
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
        start_id = job['current_id'] # Resume from last checkpoint
        end_id = job['end_id']
        job_id = job['_id']

        logger.info(f"Starting transfer job {job_id} for user {job['user_id']}: {source} -> {dest} ({start_id}-{end_id})")

        total = job['total_count']
        processed = job['processed']
        start_time = time.time()

        # Status update variables
        last_update_time = 0
        status_msg = None

        # Try to send an initial status message via BOT
        try:
            status_msg = await self.bot.send_message(
                job['user_id'],
                f"🚀 **Transfer Started**\n\nSource: `{source}`\nDest: `{dest}`\nRange: `{start_id}` - `{end_id}`"
            )
        except Exception as e:
            logger.error(f"Could not send status message: {e}")

        try:
            for msg_id in range(start_id, end_id + 1):
                # Check if cancelled externally
                current_job_status = get_active_job(job['user_id'])
                if not current_job_status:
                    logger.info("Job cancelled via DB check.")
                    break

                try:
                    # The Core Logic: Copy Message via USERBOT
                    await self.user.copy_message(
                        chat_id=dest,
                        from_chat_id=source,
                        message_id=msg_id
                    )
                    success = True
                    await asyncio.sleep(0.5)

                except errors.FloodWait as e:
                    logger.warning(f"FloodWait: Sleeping {e.value} seconds...")
                    await self.bot.send_message(job['user_id'], f"⚠️ FloodWait hit. Sleeping for {e.value}s...")
                    await asyncio.sleep(e.value)
                    # Retry
                    try:
                        await self.user.copy_message(
                            chat_id=dest,
                            from_chat_id=source,
                            message_id=msg_id
                        )
                        success = True
                    except Exception as e:
                        logger.error(f"Failed to copy {msg_id} after retry: {e}")
                        success = False

                except errors.MessageEmpty:
                    # Message doesn't exist or is empty
                    success = False
                except errors.MessageIdInvalid:
                    success = False
                except Exception as e:
                    logger.error(f"Error copying {msg_id}: {e}")
                    success = False

                # Update DB
                update_job_progress(job_id, msg_id, success)
                processed += 1

                # Update Status Message (Every 5 seconds)
                if time.time() - last_update_time > 5 and status_msg:
                    elapsed = time.time() - start_time
                    speed = processed / elapsed if elapsed > 0 else 0
                    percent = ((msg_id - job['start_id'] + 1) / total) * 100
                    remaining = total - (msg_id - job['start_id'] + 1)
                    eta = remaining / speed if speed > 0 else 0

                    text = (
                        f"📊 **Transfer Progress**\n\n"
                        f"✅ Processed: `{msg_id - job['start_id'] + 1}` / `{total}`\n"
                        f"📈 Progress: `{percent:.2f}%`\n"
                        f"⚡ Speed: `{speed:.2f} msgs/s`\n"
                        f"⏳ ETA: `{int(eta)}s`\n\n"
                        f"Processing ID: `{msg_id}`"
                    )
                    try:
                        await status_msg.edit(text)
                        last_update_time = time.time()
                    except Exception:
                        pass # Ignore edit errors (e.g., content same)

            # Completion
            complete_job(job_id)
            if status_msg:
                await status_msg.edit(
                    f"✅ **Transfer Completed!**\n\nTotal Processed: `{processed}`"
                )

        except asyncio.CancelledError:
            logger.info("Transfer task cancelled.")
            if status_msg:
                await status_msg.edit("🛑 **Transfer Cancelled.**")
            raise
        except Exception as e:
            logger.error(f"Critical Transfer Error: {e}")
            if status_msg:
                await status_msg.edit(f"❌ **Error:** {str(e)}")
        finally:
            if job['user_id'] in self.active_tasks:
                del self.active_tasks[job['user_id']]
