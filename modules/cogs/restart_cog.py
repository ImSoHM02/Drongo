import os
import sys
import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands

class RestartCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="restart", description="Restart the bot and refresh its code")
    async def restart(self, interaction: discord.Interaction):
        authorized_user_id = int(os.getenv("AUTHORIZED_USER_ID"))
        if interaction.user.id != authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        await interaction.response.send_message("Restarting bot gracefully...")

        # Schedule the restart after responding
        asyncio.create_task(self._perform_restart())

    async def _perform_restart(self):
        """Perform graceful shutdown and restart."""
        try:
            # Wait a moment for the response to send
            await asyncio.sleep(1)

            logging.info("Starting graceful restart...")

            # Perform cleanup (but don't close the bot - that kills the event loop)
            from database_modules.database import flush_message_batches
            from database_modules.database_pool import get_multi_guild_pool, close_all_pools

            # Cancel the Hypercorn server task first to free up the port
            if hasattr(self.bot, 'hypercorn_task'):
                self.bot.hypercorn_task.cancel()
                try:
                    await self.bot.hypercorn_task
                except asyncio.CancelledError:
                    pass
                logging.info("Dashboard server stopped")

            # Flush any pending database writes
            await flush_message_batches()
            logging.info("Message batches flushed")

            # Close all database pools
            await close_all_pools()
            logging.info("Database pools closed")

            # Close multi-guild pools
            multi_pool = await get_multi_guild_pool()
            await multi_pool.close_all()
            logging.info("Multi-guild pools closed")

            # Wait for everything to settle
            await asyncio.sleep(0.5)

            # Restart the process using os.execv to replace current process
            logging.info("Executing restart...")
            os.execv(sys.executable, [sys.executable] + sys.argv)

        except Exception as e:
            logging.error(f"Error during restart: {e}")
            # Still attempt to restart even if cleanup fails
            os.execv(sys.executable, [sys.executable] + sys.argv)

async def setup(bot):
    await bot.add_cog(RestartCog(bot))