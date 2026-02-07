import discord
import logging
import signal
import asyncio
import webbrowser
from discord.ext import commands
from database_modules.database import get_db_connection, initialize_database, flush_message_batches
from database_modules.database_pool import close_all_pools
from database_modules import command_database
from modules.dashboard_manager import DashboardManager
from web.dashboard import app as dashboard_app, set_bot_instance
from modules.ai import AIHandler
from modules.leveling_system import get_leveling_system
from modules.config import token, authorized_user_id, anthropic_api_key
from modules.stats_logger import StatsLogger

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])


class DrongoBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dashboard_manager = DashboardManager(self)
        self.logger = StatsLogger(self.dashboard_manager)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.anthropic_api_key = anthropic_api_key
        self.ai_handler = None
        self.leveling_system = None
        self.historical_fetcher = None
        self.start_time = None
        self.dashboard_opened = False
        self.add_listener(self.track_command_usage, 'on_interaction')

    async def setup_hook(self):
        self.dashboard_manager.start()
        self.loop.create_task(self.run_dashboard())

    async def on_ready(self):
        self.dashboard_manager.set_status("Connected")
        self.reconnect_attempts = 0
        self.logger.info(f'Logged in as {self.user}')
        self.start_time = discord.utils.utcnow()

        set_bot_instance(self)

        try:
            if self.guilds:
                await self.fetch_guild(self.guilds[0].id)
            if not self.dashboard_opened:
                webbrowser.open('http://localhost:5001')
                self.dashboard_opened = True
                self.logger.info("Dashboard opened at http://localhost:5001")
        except Exception as e:
            self.logger.warning(f"Connection may be unstable, delaying dashboard open: {e}")

        await self.setup_bot()

    async def track_command_usage(self, interaction: discord.Interaction):
        """Track slash command usage via interaction listener."""
        if interaction.type == discord.InteractionType.application_command and interaction.command:
            self.dashboard_manager.increment_command_count()
            cmd_conn = await command_database.db_connect()
            try:
                await command_database.update_command_stats(cmd_conn, str(interaction.user.id), interaction.command.name)
            except Exception as e:
                logging.error(f"Error updating command stats: {str(e)}")
            finally:
                await cmd_conn.close()

    async def on_disconnect(self):
        self.dashboard_manager.set_status("Disconnected")
        self.logger.warning("Bot disconnected")
        if not self.is_closed():
            try:
                await asyncio.sleep(5)
                if not self.is_ws_ratelimited() and not self.ws:
                    await self.attempt_reconnect()
            except Exception as e:
                logging.error(f"Error during disconnect handling: {e}")

    async def on_resumed(self):
        self.dashboard_manager.set_status("Connected")
        self.reconnect_attempts = 0
        self.logger.info("Bot reconnected")
        try:
            if self.ws and self.ws.open:
                self.logger.info("Connection verified stable")
            else:
                self.logger.warning("Connection may be unstable")
        except Exception as e:
            logging.error(f"Error checking connection stability: {e}")

    async def attempt_reconnect(self):
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            self.logger.warning(f"Attempting to reconnect... (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            try:
                await asyncio.sleep(min(5 * self.reconnect_attempts, 30))
                if not self.is_closed():
                    await self.close()
                await asyncio.sleep(1)
                await self.connect(reconnect=True)
            except Exception as e:
                logging.error(f"Reconnection attempt failed: {str(e)}")
                await asyncio.sleep(min(2 ** self.reconnect_attempts, 60))
        else:
            logging.error("Max reconnection attempts reached. Please restart the bot manually.")

    async def setup_bot(self):
        try:
            await initialize_database()
            conn = await get_db_connection()
            try:
                async with conn.execute("SELECT 1") as cursor:
                    await cursor.fetchone()
                    logging.info("Database connectivity verified")
            except Exception as db_check_error:
                logging.error(f"Database connectivity check failed: {db_check_error}")
                raise
            finally:
                await conn.close()
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            raise

        cmd_conn = await command_database.db_connect()
        try:
            await command_database.create_tables(cmd_conn)
        finally:
            await cmd_conn.close()

        await self.load_extension("modules.cogs.guild_management_cog")
        guild_cog = self.get_cog("GuildManagementCog")
        await guild_cog.initialize_existing_guilds()

        from database_modules.database_utils import migrate_guild_config_add_bot_name
        await migrate_guild_config_add_bot_name()

        self.logger.info("Loading command modules...")

        await self.load_extension("modules.cogs.maintenance_cog")
        await self.load_extension("modules.cogs.message_management_cog")
        await self.load_extension("modules.cogs.wordcount_cog")
        await self.load_extension("modules.cogs.emoji_downloader_cog")
        await self.load_extension("modules.cogs.clearchat_cog")
        await self.load_extension("modules.cogs.restart_cog")
        await self.load_extension("modules.cogs.steam_commands_cog")
        await self.load_extension("modules.cogs.wordrank_cog")
        await self.load_extension("modules.cogs.jellyfin_cog")
        await self.load_extension("modules.cogs.wow_profile_cog")
        await self.load_extension("modules.cogs.wow_main_cog")
        await self.load_extension("modules.cogs.birthday_cog")
        await self.load_extension("modules.cogs.feature_request_cog")
        await self.load_extension("modules.cogs.message_logging_cog")

        self.ai_handler = AIHandler(self, self.anthropic_api_key)
        from modules.ai.anthropic import ai
        ai.setup(self)
        await self.ai_handler.load_persisted_modes()

        self.leveling_system = get_leveling_system(self)
        self.logger.info("Leveling system initialized")

        from modules.historical_fetcher import HistoricalMessageFetcher
        self.historical_fetcher = HistoricalMessageFetcher(self)
        await self.historical_fetcher.start()
        self.logger.info("Historical message fetcher started")

        await self.load_extension("modules.cogs.leveling_cog")

        await guild_cog.sync_all_guild_commands()
        self.logger.info("Loaded all command modules.")

        logging_cog = self.get_cog("MessageLoggingCog")
        if logging_cog:
            await logging_cog.backfill_recent_messages()

    async def on_message(self, message):
        if message.author == self.user:
            return

        if self.ai_handler is not None:
            try:
                ai_response = await self.ai_handler.process_message(message)
                if ai_response:
                    message._ai_response = ai_response
            except Exception as e:
                logging.error(f"Error processing AI message: {str(e)}")

    async def run_dashboard(self):
        """Run the Quart dashboard server using Hypercorn."""
        try:
            from hypercorn.asyncio import serve
            from hypercorn.config import Config

            config = Config()
            config.bind = ["0.0.0.0:5001"]
            config.use_reloader = False

            logging.info("Starting dashboard server on port 5001...")
            self.hypercorn_task = self.loop.create_task(
                serve(dashboard_app, config)
            )
            logging.info("Dashboard server started")
        except Exception as e:
            logging.error(f"Failed to start dashboard server: {e}")


intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

bot = DrongoBot(command_prefix='!', intents=intents)
bot.authorized_user_id = authorized_user_id


def signal_handler(sig, frame):
    bot.dashboard_manager.set_status("Shutting down")

    async def shutdown():
        try:
            if hasattr(bot, 'hypercorn_task'):
                bot.hypercorn_task.cancel()
                await bot.hypercorn_task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"Error shutting down dashboard server: {e}")
        finally:
            try:
                if hasattr(bot, 'historical_fetcher') and bot.historical_fetcher:
                    await bot.historical_fetcher.stop()

                await flush_message_batches()
                await close_all_pools()

                from database_modules.database_pool import get_multi_guild_pool
                multi_pool = await get_multi_guild_pool()
                await multi_pool.close_all()
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
            finally:
                await bot.close()

    bot.loop.create_task(shutdown())


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


async def main():
    max_retries = 5
    retry_delay = 10

    for attempt in range(max_retries):
        try:
            async with bot:
                await bot.start(token)
            break

        except discord.errors.DiscordServerError as e:
            if "503" in str(e) or "Service Unavailable" in str(e):
                if attempt < max_retries - 1:
                    logging.warning(f"Discord API unavailable (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    logging.error("Failed to connect to Discord after all retry attempts.")
                    raise
            else:
                raise

        except discord.errors.HTTPException as e:
            if attempt < max_retries - 1:
                logging.warning(f"HTTP error connecting to Discord (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                logging.error("Failed to connect to Discord due to HTTP errors.")
                raise

        except Exception as e:
            logging.error(f"Unexpected error during bot startup: {e}")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except discord.errors.DiscordServerError as e:
        logging.error(f"Discord server error: {e}")
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
