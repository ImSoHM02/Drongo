import logging

import discord
from discord.ext import commands
from database_modules.database import (
    store_message, store_message_components,
    set_last_message_id, get_last_message_id
)
from database_modules import command_database


class MessageLoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if not message.guild:
            return

        await self._store_message(message)
        await self._track_command_usage(message)

    async def _store_message(self, message):
        from database_modules.database_utils import get_guild_settings, ensure_guild_database_exists
        from database_modules.database_pool import get_multi_guild_pool

        guild_settings = await get_guild_settings(str(message.guild.id))

        if not guild_settings:
            from database_modules.database_utils import add_guild_to_config
            await ensure_guild_database_exists(str(message.guild.id))
            await add_guild_to_config(str(message.guild.id), message.guild.name, logging_enabled=True)
            guild_settings = {'logging_enabled': 1}

        if not (guild_settings and guild_settings.get('logging_enabled')):
            return

        self.bot.dashboard_manager.log_message(message.author, message.guild.name, message.channel.name)

        pool = await get_multi_guild_pool()
        async with pool.get_guild_connection(str(message.guild.id)) as conn:
            try:
                clean_text = message.clean_content.strip() if message.clean_content else ""

                ai_response = self.bot.ai_responses.pop(message.id, None)
                if ai_response:
                    clean_text = f"{clean_text} {ai_response}".strip()

                message_id = await store_message(conn, message, clean_text)
                if message_id:
                    await store_message_components(message, message_id)

                await set_last_message_id(conn, message.channel.id, message.id)
            except Exception as e:
                logging.error(f"Error storing message for guild {message.guild.id}: {str(e)}")

    async def _track_command_usage(self, message):
        if message.content.startswith(('/', '!')):
            command_text = message.content[1:]
            command_name = command_text.split()[0]
            self.bot.dashboard_manager.increment_command_count()
            cmd_conn = await command_database.db_connect()
            try:
                await command_database.update_command_stats(cmd_conn, str(message.author.id), command_name)
            except Exception as e:
                logging.error(f"Error updating command stats: {str(e)}")
            finally:
                await cmd_conn.close()
        elif message.content.lower().startswith('oi drongo'):
            self.bot.dashboard_manager.increment_command_count()
            cmd_conn = await command_database.db_connect()
            try:
                await command_database.update_command_stats(cmd_conn, str(message.author.id), 'oi_drongo')
            except Exception as e:
                logging.error(f"Error updating command stats: {str(e)}")
            finally:
                await cmd_conn.close()

    async def backfill_recent_messages(self):
        """Backfill recent messages for all guilds since last processed message."""
        from database_modules.database_pool import get_multi_guild_pool

        multi_pool = await get_multi_guild_pool()
        self.bot.logger.info('Processing recent historical chat messages for all guilds...')

        for guild in self.bot.guilds:
            async with multi_pool.get_guild_connection(str(guild.id)) as conn:
                for channel in guild.text_channels:
                    try:
                        last_message_id = await get_last_message_id(conn, channel.id)
                        if last_message_id:
                            messages = [msg async for msg in channel.history(limit=200, after=discord.Object(id=last_message_id))]
                        else:
                            messages = [msg async for msg in channel.history(limit=200)]

                        for msg in reversed(messages):
                            if msg.author != self.bot.user:
                                clean_text = msg.clean_content.strip() if msg.clean_content else ""
                                message_id = await store_message(conn, msg, clean_text)
                                if message_id:
                                    await store_message_components(msg, message_id)

                        if messages:
                            await set_last_message_id(conn, channel.id, messages[-1].id)
                    except discord.Forbidden:
                        logging.debug(f"Skipping channel {channel.name} - no access")
                        continue

        self.bot.logger.info("Finished processing recent historical messages.")


async def setup(bot):
    await bot.add_cog(MessageLoggingCog(bot))
