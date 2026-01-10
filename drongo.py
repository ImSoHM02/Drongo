import discord
import os
import logging
import signal
import asyncio
import webbrowser
from discord.ext import commands
from database import store_message, store_message_components, get_db_connection, set_last_message_id, get_last_message_id, initialize_database, flush_message_batches
from database_pool import close_all_pools
import command_database
from dotenv import load_dotenv
from modules.dashboard_manager import DashboardManager
from web.dashboard_server import app as dashboard_app, set_bot_instance
from discord import Client
from modules.ai import AIHandler
from modules.leveling_system import get_leveling_system

# Set up logging
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])


# Custom logger that logs to the dashboard
class StatsLogger:
    def __init__(self, dashboard_manager):
        self.dashboard_manager = dashboard_manager

    def info(self, msg):
        self.dashboard_manager.log_event(f"INFO: {msg}")

    def warning(self, msg):
        self.dashboard_manager.log_event(f"WARNING: {msg}")

    def error(self, msg):
        self.dashboard_manager.log_event(f"ERROR: {msg}")

load_dotenv('id.env')

# Validate required environment variables
token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables")

client_id = os.getenv("DISCORD_CLIENT_ID")
if not client_id:
    raise ValueError("DISCORD_CLIENT_ID is not set in the environment variables")

authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
my_user_id = os.getenv("BLACKTHENWHITE_USER_ID")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")

# Log environment validation success (without exposing sensitive data)
logging.info("Environment variables validated successfully")

class HeartbeatClient(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heartbeat_timeout = 60  # Increased timeout to avoid conflicts
        self.heartbeat_task = None
        self._heartbeat_lock = asyncio.Lock()
        self.reconnecting = False
        
    async def heartbeat(self):
        try:
            while not self.is_closed():
                async with self._heartbeat_lock:
                    if self.ws is not None and self.ws.open:
                        try:
                            await self.ws.ping()
                        except Exception as e:
                            logging.error(f"Heartbeat ping failed: {e}")
                await asyncio.sleep(self.heartbeat_timeout)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logging.error(f"Heartbeat task error: {e}")

    async def on_connect(self):
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
        self.heartbeat_task = self.loop.create_task(self.heartbeat())

    async def on_disconnect(self):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None

class DrongoBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, client_class=HeartbeatClient)
        self.dashboard_manager = DashboardManager(self)
        self.logger = StatsLogger(self.dashboard_manager)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.anthropic_api_key = anthropic_api_key
        self.ai_handler = None  # Initialize ai_handler as None
        self.leveling_system = None  # Initialize leveling_system as None
        self.historical_fetcher = None  # Initialize historical_fetcher as None
        self.start_time = None  # Will be set when bot is ready
        self.dashboard_opened = False
        self.add_listener(self.track_command_usage, 'on_interaction')

    async def setup_hook(self):
        self.dashboard_manager.start()
        
        # Start the dashboard server
        self.loop.create_task(self.run_dashboard())
        
        # Start periodic maintenance task
        self.loop.create_task(self.periodic_maintenance())
    
    async def periodic_maintenance(self):
        """Periodic maintenance task for database optimization."""
        while not self.is_closed():
            try:
                # Wait 5 minutes between maintenance cycles
                await asyncio.sleep(300)
                
                # Flush any pending message batches
                await flush_message_batches()
                
                # Every hour, do more intensive maintenance
                if hasattr(self, '_maintenance_counter'):
                    self._maintenance_counter += 1
                else:
                    self._maintenance_counter = 1
                    
                if self._maintenance_counter >= 12:  # Every hour (12 * 5 minutes)
                    self._maintenance_counter = 0

                    # Cleanup inactive guild database pools
                    try:
                        from database_pool import get_multi_guild_pool
                        multi_pool = await get_multi_guild_pool()
                        await multi_pool.cleanup_inactive_pools()
                    except Exception as e:
                        logging.error(f"Error cleaning up inactive pools: {e}")

                    self.logger.info("Performed periodic database maintenance")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error in periodic maintenance: {e}")

    async def on_ready(self):
        self.dashboard_manager.set_status("Connected")
        self.reconnect_attempts = 0
        self.logger.info(f'Logged in as {self.user}')
        self.start_time = discord.utils.utcnow()  # Set bot start time
        
        # Set bot instance for dashboard name resolution
        set_bot_instance(self)
        
        # Verify connection is stable before opening dashboard
        try:
            # Touch a simple API call if guilds are available to ensure connectivity
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
        """Listener to track slash command usage."""
        if interaction.type == discord.InteractionType.application_command and interaction.command:
            # Update dashboard command counter
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
        # Don't attempt reconnect here - let Discord.py handle initial reconnection
        if not self.is_closed():
            try:
                await asyncio.sleep(5)  # Wait before checking connection
                if not self.is_ws_ratelimited() and not self.ws:
                    await self.attempt_reconnect()
            except Exception as e:
                logging.error(f"Error during disconnect handling: {e}") # Use standard logging

    async def on_resumed(self):
        self.dashboard_manager.set_status("Connected")
        self.reconnect_attempts = 0  # Reset reconnect attempts on successful reconnection
        self.logger.info("Bot reconnected")
        # Verify connection is stable
        try:
            if self.ws and self.ws.open:
                self.logger.info("Connection verified stable")
            else:
                self.logger.warning("Connection may be unstable")
        except Exception as e:
            logging.error(f"Error checking connection stability: {e}") # Use standard logging

    async def attempt_reconnect(self):
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            self.logger.warning(f"Attempting to reconnect... (Attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            try:
                # Add delay between reconnection attempts
                await asyncio.sleep(min(5 * self.reconnect_attempts, 30))
                if not self.is_closed():
                    await self.close()
                await asyncio.sleep(1)
                await self.connect(reconnect=True)
            except Exception as e:
                logging.error(f"Reconnection attempt failed: {str(e)}") # Use standard logging
                # Add exponential backoff
                await asyncio.sleep(min(2 ** self.reconnect_attempts, 60))
        else:
            logging.error("Max reconnection attempts reached. Please restart the bot manually.") # Use standard logging

    async def setup_bot(self):
        # Initialize databases with optimizations
        try:
            await initialize_database()
            
            # Leveling system database initialization
            # Note: Automatic migration removed for performance optimization
            # Database schema is now properly configured and migration overhead is unnecessary
            # Migration can be run manually if needed using tools/migrations/migrate_leveling_database.py
            
            # Verify database exists and is accessible
            conn = await get_db_connection()
            try:
                # Simple query to verify database connectivity
                async with conn.execute("SELECT 1") as cursor:
                    result = await cursor.fetchone()
                    if result:
                        logging.info("Database connectivity verified")
            except Exception as db_check_error:
                logging.error(f"Database connectivity check failed: {db_check_error}")
                raise
            finally:
                await conn.close()
            
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            raise  # Re-raise to prevent bot from continuing with broken database
            
        # Initialize command stats database
        cmd_conn = await command_database.db_connect()
        try:
            await command_database.create_tables(cmd_conn)
        finally:
            await cmd_conn.close()

        # Initialize guild databases for multi-guild chat history
        await self.initialize_existing_guilds()

        # PRIORITY: Load commands FIRST before processing messages
        self.logger.info("Loading command modules...")
        
        # Load Cogs
        await self.load_extension("modules.cogs.message_management_cog")
        await self.load_extension("modules.cogs.wordcount_cog")
        await self.load_extension("modules.cogs.emoji_downloader_cog")
        await self.load_extension("modules.cogs.clearchat_cog")
        await self.load_extension("modules.cogs.message_stats_cog")
        await self.load_extension("modules.cogs.restart_cog")
        await self.load_extension("modules.cogs.steam_commands_cog")
        await self.load_extension("modules.cogs.wordrank_cog")
        await self.load_extension("modules.cogs.jellyfin_cog")

        # Initialize and set up AI handler
        self.ai_handler = AIHandler(self, self.anthropic_api_key)
        from modules.ai.anthropic import ai
        ai.setup(self)
        
        # Initialize leveling system
        self.leveling_system = get_leveling_system(self)
        self.logger.info("Leveling system initialized")

        # Initialize historical message fetcher
        from modules.historical_fetcher import HistoricalMessageFetcher
        self.historical_fetcher = HistoricalMessageFetcher(self)
        await self.historical_fetcher.start()
        self.logger.info("Historical message fetcher started")
        
        # Log commands before sync
        self.logger.info(f"Commands before sync: {[cmd.name for cmd in self.tree.get_commands()]}")
        
        # Sync application commands (BEFORE loading leveling cog)
        await self.tree.sync()
        self.logger.info("Initial command sync completed (before cogs)")

        # Load remaining Cogs
        await self.load_extension("modules.cogs.web_link_cog")
        
        # Load version tracker after AI handler is initialized
        await self.load_extension("modules.cogs.version_tracker_cog")
        
        # Load database management cog
        await self.load_extension("modules.cogs.database_management_cog")
        
        # Load leveling cog
        await self.load_extension("modules.cogs.leveling_cog")
        
        # Log commands after loading leveling cog
        self.logger.info(f"Commands after loading leveling cog: {[cmd.name for cmd in self.tree.get_commands()]}")
        
        # Sync commands again after loading leveling cog
        await self.tree.sync()
        self.logger.info("Final command sync completed (after leveling cog)")

        # Ensure primary guild has the latest commands immediately
        self.logger.info("Loaded all command modules.")
        
        # NOW process recent historical messages for all guilds after commands are loaded
        from database_pool import get_multi_guild_pool
        multi_pool = await get_multi_guild_pool()
        self.logger.info('Processing recent historical chat messages for all guilds...')
        for guild in self.guilds:
            async with multi_pool.get_guild_connection(str(guild.id)) as conn:
                for channel in guild.text_channels:
                    last_message_id = await get_last_message_id(conn, channel.id)
                    if last_message_id:
                        messages = [message async for message in channel.history(limit=200, after=discord.Object(id=last_message_id))]
                    else:
                        messages = [message async for message in channel.history(limit=200)]

                    for message in reversed(messages):
                        if message.author != self.user:  # Allow bot messages during setup
                            # Extract clean text only
                            clean_text = message.clean_content.strip() if message.clean_content else ""

                            # Store clean text
                            message_id = await store_message(conn, message, clean_text)

                            # Store components separately
                            if message_id:
                                await store_message_components(message, message_id)

                    if messages:
                        await set_last_message_id(conn, channel.id, messages[-1].id)

        self.logger.info("Finished processing recent historical messages.")


    async def on_message(self, message):
        try:
            if message.author == self.user:  # Only exclude our own messages
                return

            # Update message count
            # This will be handled by the dashboard server querying the database
            
            # Process AI response for all guilds if ai_handler is initialized
            ai_response = None
            if self.ai_handler is not None:
                try:
                    ai_response = await self.ai_handler.process_message(message)
                except Exception as e:
                    logging.error(f"Error processing AI message: {str(e)}") # Use standard logging

            try:
                # Extract clean text only (no URLs, no attachments, no embed text)
                clean_text = message.clean_content.strip() if message.clean_content else ""

                # Append AI response to clean text if present
                if ai_response:
                    clean_text = f"{clean_text} {ai_response}".strip()

                # Only process messages that occur after bot start
                if message.created_at >= self.start_time:
                    # Process XP award asynchronously to avoid blocking message processing
                    if self.leveling_system and message.guild:
                        asyncio.create_task(self._process_xp_award(message))

                # Store messages for all guilds (multi-guild support)
                if message.guild:
                    from database_utils import get_guild_settings, ensure_guild_database_exists
                    from database_pool import get_multi_guild_pool

                    # Check if logging is enabled for this guild
                    guild_settings = await get_guild_settings(str(message.guild.id))

                    # If guild not in config yet, initialize it
                    if not guild_settings:
                        from database_utils import add_guild_to_config
                        await ensure_guild_database_exists(str(message.guild.id))
                        await add_guild_to_config(str(message.guild.id), message.guild.name, logging_enabled=True)
                        guild_settings = {'logging_enabled': 1}

                    # Only store if logging is enabled
                    if guild_settings and guild_settings.get('logging_enabled'):
                        # Log the message in the dashboard (for all guilds now)
                        self.dashboard_manager.log_message(message.author, message.guild.name, message.channel.name)

                        # Use guild-specific database connection
                        pool = await get_multi_guild_pool()
                        async with pool.get_guild_connection(str(message.guild.id)) as conn:
                            try:
                                # Store clean text only in messages table
                                message_id = await store_message(conn, message, clean_text)

                                # Store components (attachments, embeds, URLs) in separate databases
                                if message_id:
                                    await store_message_components(message, message_id)

                                # Update last message tracking
                                await set_last_message_id(conn, message.channel.id, message.id)
                            except Exception as e:
                                logging.error(f"Error storing message for guild {message.guild.id}: {str(e)}") # Use standard logging

                # Track command usage in separate database
                if message.content.startswith(('/', '!')):  # Track both slash and ! commands
                    command_text = message.content[1:]  # Remove the prefix (/ or !)
                    command_name = command_text.split()[0]  # Get just the command name
                    
                    # Update dashboard command counter
                    self.dashboard_manager.increment_command_count()
                    
                    cmd_conn = await command_database.db_connect()
                    try:
                        await command_database.update_command_stats(cmd_conn, str(message.author.id), command_name)
                    except Exception as e:
                        logging.error(f"Error updating command stats: {str(e)}") # Use standard logging
                    finally:
                        await cmd_conn.close()
                
                # Track "oi drongo" usage in separate database
                elif message.content.lower().startswith('oi drongo'):
                    # Update dashboard command counter
                    self.dashboard_manager.increment_command_count()
                    
                    cmd_conn = await command_database.db_connect()
                    try:
                        await command_database.update_command_stats(cmd_conn, str(message.author.id), 'oi_drongo')
                    except Exception as e:
                        logging.error(f"Error updating command stats: {str(e)}") # Use standard logging
                    finally:
                        await cmd_conn.close()
                
                # await self.process_commands(message) # This is for prefix commands, which are not used.
            except Exception as e:
                logging.error(f"Error processing message content: {str(e)}") # Use standard logging
        except Exception as e:
            logging.error(f"Unhandled error in message processing: {str(e)}") # Use standard logging

    async def _process_xp_award(self, message: discord.Message):
        """Process XP award for a message asynchronously."""
        try:
            result = await self.leveling_system.process_message(message)
            if result and result.get('level_up'):
                # Handle level up announcements
                await self._handle_level_up_announcement(message, result)
        except Exception as e:
            logging.error(f"Error processing XP award: {e}")

    async def _handle_level_up_announcement(self, message: discord.Message, level_result: dict):
        """Handle level up announcements."""
        try:
            # Get guild configuration for announcements
            config = await self.leveling_system.get_guild_config(str(message.guild.id))
            
            if not config.get('level_up_announcements', True):
                return
                
            old_level = level_result['old_level']
            new_level = level_result['new_level']
            
            # Create level up message using configured template
            level_up_message = await self.leveling_system.get_level_up_message(
                str(message.author.id), str(message.guild.id), old_level, new_level
            )
            
            # Append rank title to announcement if configured
            rank_info = await self.leveling_system.get_user_rank(str(message.author.id), str(message.guild.id))
            if rank_info and rank_info.get('rank_title'):
                level_up_message += f" • {rank_info['rank_title']}"
            # Send to announcement channel if configured, otherwise use current channel
            announcement_channel_id = config.get('announcement_channel_id')
            if announcement_channel_id:
                try:
                    channel = self.get_channel(int(announcement_channel_id))
                    if channel:
                        await channel.send(level_up_message)
                    else:
                        # Fall back to current channel if announcement channel not found
                        await message.channel.send(level_up_message)
                except:
                    await message.channel.send(level_up_message)
            else:
                await message.channel.send(level_up_message)
                
            # Send DM notification if enabled
            if config.get('dm_level_notifications', False):
                try:
                    await message.author.send(f"🎉 You leveled up in **{message.guild.name}**! You are now **Level {new_level}**!")
                except:
                    # User may have DMs disabled
                    pass
                    
        except Exception as e:
            logging.error(f"Error handling level up announcement: {e}")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle reaction achievements."""
        if payload.member.bot:
            return

        channel = self.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # Only process reactions that occur after bot start
        if message.created_at < self.start_time:
            return
        
        # Create a custom reaction object with the necessary attributes
        class CustomReaction:
            def __init__(self, emoji, member):
                self.emoji = emoji
                self.member = member
                self.message = message

        reaction = CustomReaction(payload.emoji, payload.member)
        # Removed achievement check for reactions

    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        from database_utils import (
            ensure_guild_database_exists,
            add_guild_to_config,
            queue_channel_for_historical_fetch
        )

        try:
            self.logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

            # Ensure database structure exists
            was_created = await ensure_guild_database_exists(str(guild.id))

            # Add to guild configuration
            await add_guild_to_config(str(guild.id), guild.name, logging_enabled=True)

            # Queue all text channels for historical fetching
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

            self.logger.info(f"Initialized guild {guild.name} for chat history logging")

        except Exception as e:
            logging.error(f"Error handling guild join: {e}")

    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot leaves a guild."""
        from database_utils import update_guild_logging
        from database_pool import get_multi_guild_pool

        try:
            self.logger.info(f"Left guild: {guild.name} (ID: {guild.id})")

            # Disable logging for this guild (don't delete data)
            await update_guild_logging(str(guild.id), False)

            # Close database pool for this guild to free resources
            pool = await get_multi_guild_pool()
            if str(guild.id) in pool.guild_pools:
                guild_pool = pool.guild_pools.pop(str(guild.id))
                await guild_pool.close_all()
                pool.last_accessed.pop(str(guild.id), None)

            self.logger.info(f"Disabled logging for guild {guild.name}")

        except Exception as e:
            logging.error(f"Error handling guild remove: {e}")

    async def initialize_existing_guilds(self):
        """Initialize databases for all guilds the bot is currently in."""
        from database_utils import (
            ensure_guild_database_exists,
            add_guild_to_config,
            queue_channel_for_historical_fetch,
            initialize_guild_config_db
        )

        try:
            # Initialize the global config database first
            await initialize_guild_config_db()

            for guild in self.guilds:
                try:
                    # Ensure database exists
                    was_created = await ensure_guild_database_exists(str(guild.id))

                    # Add to guild configuration
                    await add_guild_to_config(str(guild.id), guild.name, logging_enabled=True)

                    # If database was just created, queue channels for historical fetch
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
                        self.logger.info(f"Initialized new database for existing guild: {guild.name}")
                    else:
                        self.logger.info(f"Database already exists for guild: {guild.name}")

                except Exception as e:
                    logging.error(f"Error initializing guild {guild.name}: {e}")

        except Exception as e:
            logging.error(f"Error initializing existing guilds: {e}")

    async def run_dashboard(self):
        """Run the Quart dashboard server using Hypercorn."""
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = ["0.0.0.0:5001"]
        config.use_reloader = False
        
        self.hypercorn_task = self.loop.create_task(
            serve(dashboard_app, config)
        )

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
            # Cancel the Hypercorn server task
            if hasattr(bot, 'hypercorn_task'):
                bot.hypercorn_task.cancel()
                await bot.hypercorn_task
        except asyncio.CancelledError:
            pass  # Expected
        except Exception as e:
            logging.error(f"Error shutting down dashboard server: {e}")
        finally:
            try:
                # Stop historical fetcher
                if hasattr(bot, 'historical_fetcher') and bot.historical_fetcher:
                    await bot.historical_fetcher.stop()

                await flush_message_batches()
                await close_all_pools()

                # Close multi-guild pools
                from database_pool import get_multi_guild_pool
                multi_pool = await get_multi_guild_pool()
                await multi_pool.close_all()

            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
            finally:
                await bot.close()
    
    # Run shutdown task
    bot.loop.create_task(shutdown())

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    """Main function with Discord connection retry logic."""
    max_retries = 5
    retry_delay = 10  # seconds
    
    for attempt in range(max_retries):
        try:
            async with bot:
                await bot.start(token)
            break  # If successful, break out of the retry loop
            
        except discord.errors.DiscordServerError as e:
            if "503" in str(e) or "Service Unavailable" in str(e):
                if attempt < max_retries - 1:
                    logging.warning(f"Discord API unavailable (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logging.error("Failed to connect to Discord after all retry attempts. Discord API may be down.")
                    logging.error("Check Discord status at: https://discordstatus.com/")
                    raise
            else:
                # Re-raise other Discord errors
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
            # For other exceptions, don't retry
            logging.error(f"Unexpected error during bot startup: {e}")
            raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except discord.errors.DiscordServerError as e:
        logging.error(f"Discord server error: {e}")
        logging.error("This is likely a temporary Discord API issue. Please try again later.")
    except Exception as e:
        logging.error(f"Failed to start bot: {e}")
