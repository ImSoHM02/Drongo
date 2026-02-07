import asyncio
import logging

import discord
from discord.ext import commands
from database_modules.command_overrides import get_command_overrides


class GuildManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._command_sync_lock = asyncio.Lock()
        self._global_commands_cleared = False

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        from database_modules.database_utils import (
            ensure_guild_database_exists,
            add_guild_to_config,
            queue_channel_for_historical_fetch
        )

        try:
            self.bot.logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

            was_created = await ensure_guild_database_exists(str(guild.id))
            await add_guild_to_config(str(guild.id), guild.name, logging_enabled=True)

            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).read_message_history:
                    await queue_channel_for_historical_fetch(
                        str(guild.id),
                        str(channel.id),
                        channel.name,
                        priority=1 if was_created else 0,
                        force=True,
                        reset_progress=was_created
                    )

            self.bot.logger.info(f"Initialized guild {guild.name} for chat history logging")

        except Exception as e:
            logging.error(f"Error handling guild join: {e}")
        else:
            try:
                await self.sync_guild_commands(str(guild.id))
            except Exception as sync_error:
                logging.error(f"Error syncing commands for new guild {guild.id}: {sync_error}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot leaves a guild."""
        from database_modules.database_utils import update_guild_logging
        from database_modules.database_pool import get_multi_guild_pool

        try:
            self.bot.logger.info(f"Left guild: {guild.name} (ID: {guild.id})")

            await update_guild_logging(str(guild.id), False)

            pool = await get_multi_guild_pool()
            if str(guild.id) in pool.guild_pools:
                guild_pool = pool.guild_pools.pop(str(guild.id))
                await guild_pool.close_all()
                pool.last_accessed.pop(str(guild.id), None)

            self.bot.logger.info(f"Disabled logging for guild {guild.name}")

        except Exception as e:
            logging.error(f"Error handling guild remove: {e}")

    async def initialize_existing_guilds(self):
        """Initialize databases for all guilds the bot is currently in."""
        from database_modules.database_utils import (
            ensure_guild_database_exists,
            add_guild_to_config,
            queue_channel_for_historical_fetch,
            initialize_guild_config_db
        )

        try:
            await initialize_guild_config_db()

            for guild in self.bot.guilds:
                try:
                    was_created = await ensure_guild_database_exists(str(guild.id))
                    await add_guild_to_config(str(guild.id), guild.name, logging_enabled=True)

                    if was_created:
                        for channel in guild.text_channels:
                            if channel.permissions_for(guild.me).read_message_history:
                                await queue_channel_for_historical_fetch(
                                    str(guild.id),
                                    str(channel.id),
                                    channel.name,
                                    priority=0,
                                    force=True,
                                    reset_progress=True
                                )
                        self.bot.logger.info(f"Initialized new database for existing guild: {guild.name}")
                    else:
                        self.bot.logger.info(f"Database already exists for guild: {guild.name}")

                except Exception as e:
                    logging.error(f"Error initializing guild {guild.name}: {e}")

        except Exception as e:
            logging.error(f"Error initializing existing guilds: {e}")

    async def _clear_global_commands(self):
        """Remove global commands so guild-specific sets control visibility."""
        if self._global_commands_cleared:
            return

        application_id = self.bot.application_id or (self.bot.user.id if self.bot.user else None)
        if not application_id:
            logging.warning("Cannot clear global commands: application_id is not available")
            return

        try:
            await self.bot.http.bulk_upsert_global_commands(application_id, [])
            self._global_commands_cleared = True
            self.bot.logger.info("Cleared global commands before guild sync")
        except Exception as e:
            logging.error(f"Failed to clear global commands: {e}")

    async def sync_guild_commands(self, guild_id: str):
        """Sync commands for a single guild, applying per-guild overrides."""
        async with self._command_sync_lock:
            await self._clear_global_commands()

            guild_obj = discord.Object(id=int(guild_id))
            overrides = await get_command_overrides(guild_id)
            disabled = {name.lower() for name, enabled in overrides.items() if not enabled}

            self.bot.tree.clear_commands(guild=guild_obj)
            self.bot.tree.copy_global_to(guild=guild_obj)

            for command in list(self.bot.tree.get_commands(guild=guild_obj)):
                if command.name.lower() in disabled:
                    cmd_type = getattr(command, "type", discord.AppCommandType.chat_input)
                    self.bot.tree.remove_command(command.name, type=cmd_type, guild=guild_obj)

            synced = await self.bot.tree.sync(guild=guild_obj)
            self.bot.logger.info(
                f"Synced {len(synced)} commands for guild {guild_id} (disabled: {sorted(disabled) if disabled else 'none'})"
            )
            return synced

    async def sync_all_guild_commands(self):
        """Sync commands for all connected guilds using stored overrides."""
        if not self.bot.guilds:
            self.bot.logger.info("No guilds available for command sync")
            return

        for guild in self.bot.guilds:
            try:
                await self.sync_guild_commands(str(guild.id))
            except Exception as e:
                logging.error(f"Failed to sync commands for guild {guild.id}: {e}")


async def setup(bot):
    await bot.add_cog(GuildManagementCog(bot))
