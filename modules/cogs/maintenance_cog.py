import logging
from discord.ext import commands, tasks
from database_modules.database import flush_message_batches


class MaintenanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._maintenance_counter = 0

    async def cog_load(self):
        self.periodic_maintenance.start()

    async def cog_unload(self):
        self.periodic_maintenance.cancel()

    @tasks.loop(minutes=5)
    async def periodic_maintenance(self):
        try:
            await flush_message_batches()

            self._maintenance_counter += 1
            if self._maintenance_counter >= 12:
                self._maintenance_counter = 0
                try:
                    from database_modules.database_pool import get_multi_guild_pool
                    multi_pool = await get_multi_guild_pool()
                    await multi_pool.cleanup_inactive_pools()
                except Exception as e:
                    logging.error(f"Error cleaning up inactive pools: {e}")
                self.bot.logger.info("Performed periodic database maintenance")
        except Exception as e:
            logging.error(f"Error in periodic maintenance: {e}")

    @periodic_maintenance.before_loop
    async def before_maintenance(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(MaintenanceCog(bot))
