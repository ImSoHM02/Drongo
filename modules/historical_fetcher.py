import asyncio
import logging
from datetime import datetime
from typing import Optional
import discord
import aiosqlite

class HistoricalMessageFetcher:
    """
    Background task that fetches historical messages from Discord channels
    and stores them in the guild-specific databases.
    """

    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.current_job = None
        self.fetch_task = None
        self.stats = {
            'messages_fetched': 0,
            'channels_completed': 0,
            'errors': 0,
            'channels_in_progress': 0
        }

    async def start(self):
        """Start the background fetch task."""
        if self.running:
            logging.warning("Historical fetcher already running")
            return
        
        # Recover any jobs that were left in-progress from a previous shutdown
        await self._reset_stuck_jobs()

        self.running = True
        self.fetch_task = asyncio.create_task(self._fetch_loop())
        logging.info("Historical message fetcher started")

    async def stop(self):
        """Stop the background fetch task."""
        self.running = False
        if self.fetch_task:
            self.fetch_task.cancel()
            try:
                await self.fetch_task
            except asyncio.CancelledError:
                pass
        logging.info("Historical message fetcher stopped")

    async def _fetch_loop(self):
        """Main fetch loop that processes the queue."""
        while self.running:
            try:
                # Get next job from queue
                job = await self._get_next_job()

                if not job:
                    # No jobs in queue, wait before checking again
                    await asyncio.sleep(60)
                    continue

                # Process the job
                await self._process_job(job)

                # Rate limiting: wait 1 second between batches
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in historical fetch loop: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(5)

    async def _get_next_job(self) -> Optional[dict]:
        """Get the next channel to fetch from the queue."""
        from database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        async with aiosqlite.connect(config_db_path) as conn:
            # Get highest priority pending job
            async with conn.execute("""
                SELECT id, guild_id, channel_id, channel_name
                FROM fetch_queue
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()

                if not row:
                    return None

                job_id, guild_id, channel_id, channel_name = row

                # Mark as in_progress
                await conn.execute("""
                    UPDATE fetch_queue
                    SET status = 'in_progress', started_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), job_id))

                await conn.commit()

                return {
                    'id': job_id,
                    'guild_id': guild_id,
                    'channel_id': channel_id,
                    'channel_name': channel_name
                }

    async def _process_job(self, job: dict):
        """Process a single fetch job."""
        guild_id = job['guild_id']
        channel_id = job['channel_id']
        channel_name = job['channel_name']

        try:
            # Get the guild and channel
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                logging.warning(f"Guild {guild_id} not found, marking job as completed")
                await self._mark_job_completed(job['id'], success=False)
                return

            channel = guild.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.TextChannel):
                logging.warning(f"Channel {channel_id} not found or not a text channel, marking job as completed")
                await self._mark_job_completed(job['id'], success=False)
                return

            # Check permissions
            if not channel.permissions_for(guild.me).read_message_history:
                logging.warning(f"No permission to read history in {channel_name}, marking job as completed")
                await self._mark_job_completed(job['id'], success=False)
                return

            # Get progress info
            progress = await self._get_fetch_progress(guild_id, channel_id)
            last_message_id = progress.get('last_fetched_message_id')

            # Fetch messages
            messages_fetched = 0
            oldest_message_id = None

            # Fetch up to 100 messages (Discord API limit per request)
            before_id = int(last_message_id) if last_message_id else None

            try:
                if before_id:
                    messages = [msg async for msg in channel.history(limit=100, before=discord.Object(id=before_id))]
                else:
                    messages = [msg async for msg in channel.history(limit=100)]
            except discord.Forbidden:
                logging.warning(f"Forbidden to read history in {channel_name}")
                await self._mark_job_completed(job['id'], success=False)
                return
            except discord.HTTPException as e:
                logging.error(f"HTTP error fetching history from {channel_name}: {e}")
                await self._mark_job_completed(job['id'], success=False, error=str(e))
                return

            if not messages:
                # No more messages to fetch
                logging.info(f"Completed fetching history for {channel_name} in guild {guild.name}")
                await self._mark_channel_fetch_completed(guild_id, channel_id)
                await self._mark_job_completed(job['id'], success=True)
                self.stats['channels_completed'] += 1
                return

            # Store messages in guild database
            messages_fetched = await self._store_historical_messages(guild_id, messages)

            # Update progress
            oldest_message_id = str(messages[-1].id)
            total_fetched = progress.get('total_fetched', 0) + messages_fetched

            await self._update_fetch_progress(
                guild_id,
                channel_id,
                oldest_message_id,
                total_fetched
            )

            # Re-queue for next batch
            await self._requeue_job(job['id'])

            self.stats['messages_fetched'] += messages_fetched
            logging.info(f"Fetched {messages_fetched} messages from {channel_name} (total: {total_fetched})")

        except Exception as e:
            logging.error(f"Error processing fetch job for {channel_name}: {e}")
            self.stats['errors'] += 1
            await self._mark_job_completed(job['id'], success=False, error=str(e))

    async def _store_historical_messages(self, guild_id: str, messages: list) -> int:
        """Store fetched messages in the guild database."""
        from database_pool import get_multi_guild_pool
        from database import store_message

        stored_count = 0

        pool = await get_multi_guild_pool()
        async with pool.get_guild_connection(guild_id) as conn:
            for message in reversed(messages):  # Store in chronological order
                try:
                    # Build full message content
                    message_parts = []

                    if message.clean_content.strip():
                        message_parts.append(message.clean_content.strip())

                    if message.attachments:
                        message_parts.append(' '.join(attachment.url for attachment in message.attachments))

                    if message.embeds:
                        embed_fields = []
                        for embed in message.embeds:
                            if embed.fields:
                                for field in embed.fields:
                                    embed_fields.append(f"{field.name}: {field.value}")
                        if embed_fields:
                            message_parts.append(' '.join(embed_fields))

                    full_message_content = ' '.join(message_parts)

                    if full_message_content:
                        await store_message(conn, message, full_message_content)
                        stored_count += 1

                except Exception as e:
                    logging.error(f"Error storing historical message {message.id}: {e}")

        return stored_count

    async def _get_fetch_progress(self, guild_id: str, channel_id: str) -> dict:
        """Get fetch progress for a channel."""
        from database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        async with aiosqlite.connect(config_db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT * FROM historical_fetch_progress
                WHERE guild_id = ? AND channel_id = ?
            """, (guild_id, channel_id)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return {}

    async def _update_fetch_progress(self, guild_id: str, channel_id: str, last_message_id: str, total_fetched: int):
        """Update fetch progress for a channel."""
        from database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        async with aiosqlite.connect(config_db_path) as conn:
            await conn.execute("""
                UPDATE historical_fetch_progress
                SET last_fetched_message_id = ?,
                    oldest_message_id = ?,
                    total_fetched = ?,
                    last_fetch_timestamp = ?,
                    is_scanning = 1
                WHERE guild_id = ? AND channel_id = ?
            """, (last_message_id, last_message_id, total_fetched, datetime.now().isoformat(), guild_id, channel_id))

            await conn.commit()

    async def _mark_channel_fetch_completed(self, guild_id: str, channel_id: str):
        """Mark a channel as completely fetched."""
        from database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        async with aiosqlite.connect(config_db_path) as conn:
            await conn.execute("""
                UPDATE historical_fetch_progress
                SET fetch_completed = 1,
                    is_scanning = 0,
                    last_fetch_timestamp = ?
                WHERE guild_id = ? AND channel_id = ?
            """, (datetime.now().isoformat(), guild_id, channel_id))

            await conn.commit()

    async def _mark_job_completed(self, job_id: int, success: bool = True, error: str = None):
        """Mark a fetch job as completed."""
        from database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        async with aiosqlite.connect(config_db_path) as conn:
            await conn.execute("""
                UPDATE fetch_queue
                SET status = 'completed',
                    completed_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), job_id))

            await conn.commit()

    async def _requeue_job(self, job_id: int):
        """Re-queue a job for the next batch."""
        from database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        async with aiosqlite.connect(config_db_path) as conn:
            await conn.execute("""
                UPDATE fetch_queue
                SET status = 'pending',
                    started_at = NULL
                WHERE id = ?
            """, (job_id,))

            await conn.commit()

    def get_stats(self) -> dict:
        """Get current fetcher statistics."""
        return self.stats.copy()

    async def _reset_stuck_jobs(self):
        """Reset any jobs left in 'in_progress' after an unexpected shutdown."""
        from database_schema import get_guild_config_db_path

        config_db_path = get_guild_config_db_path()

        async with aiosqlite.connect(config_db_path) as conn:
            cursor = await conn.execute("""
                UPDATE fetch_queue
                SET status = 'pending',
                    started_at = NULL
                WHERE status = 'in_progress'
            """)
            await conn.commit()

            if cursor.rowcount and cursor.rowcount > 0:
                logging.info(f"Reset {cursor.rowcount} stuck historical fetch jobs to pending")
