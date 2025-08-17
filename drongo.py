import discord
import os
import logging
import signal
import sys
import asyncio
import webbrowser
from discord.ext import commands
from database import (create_table, store_message, get_db_connection,
                      set_last_message_id, get_last_message_id,
                      create_game_tracker_tables, track_voice_join,
                      track_voice_leave, get_user_voice_stats,
                      get_voice_leaderboard, initialize_database,
                      store_message_optimized, flush_message_batches)
from database_pool import close_all_pools
import command_database
from dotenv import load_dotenv
from modules.dashboard_manager import DashboardManager
from web.dashboard_server import app as dashboard_app
from discord import Client
from modules.ai import AIHandler

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

guild_id_env = os.getenv("DISCORD_GUILD_ID")
if not guild_id_env:
    raise ValueError("DISCORD_GUILD_ID is not set in the environment variables")

primary_guild_id = guild_id_env.split(',')[0].strip()  # Get first guild ID for logging
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
                    # Could add more maintenance tasks here
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
        
        # Verify connection is stable before opening dashboard
        try:
            # Test connection with a simple API call
            await self.fetch_guild(int(primary_guild_id))
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
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            
        # Initialize command stats database
        cmd_conn = await command_database.db_connect()
        try:
            await command_database.create_tables(cmd_conn)
        finally:
            await cmd_conn.close()
            
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
        
        # Sync application commands
        await self.tree.sync()

        # Load remaining Cogs
        await self.load_extension("modules.cogs.web_link_cog")
        
        # Load version tracker after AI handler is initialized
        await self.load_extension("modules.cogs.version_tracker_cog")
        
        # Load database management cog
        await self.load_extension("modules.cogs.database_management_cog")
        
        self.logger.info("Loaded all command modules.")
        
        # NOW process historical messages after commands are loaded
        conn = None
        try:
            conn = await get_db_connection()
            self.logger.info('Processing historical chat messages...')
            for guild in self.guilds:
                # Only process messages for the primary guild
                if str(guild.id) == primary_guild_id:
                    for channel in guild.text_channels:
                        last_message_id = await get_last_message_id(conn, channel.id)
                        if last_message_id:
                            messages = [message async for message in channel.history(limit=200, after=discord.Object(id=last_message_id))]
                        else:
                            messages = [message async for message in channel.history(limit=200)]

                        for message in reversed(messages):
                            if message.author != self.user:  # Allow bot messages during setup
                                # Store message in database but don't process for achievements
                                # This prevents achievements from triggering on historical messages during setup
                                # Combine message content, attachments, and embed fields
                                attachment_urls = ' '.join([attachment.url for attachment in message.attachments])
                                embed_content = []
                                for embed in message.embeds:
                                    for field in embed.fields:
                                        embed_content.append(f"{field.name}: {field.value}")
                                full_message_content = f"{message.clean_content} {attachment_urls} {' '.join(embed_content)}".strip()
                                await store_message(conn, message, full_message_content)
                        if messages:
                            await set_last_message_id(conn, channel.id, messages[-1].id)

            self.logger.info("Finished processing historical messages.")

        finally:
            if conn:
                await conn.close()


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
                # Store message content and any attachments/embeds
                message_parts = []
                
                # Add main message content
                if message.clean_content.strip():
                    message_parts.append(message.clean_content.strip())
                
                # Add attachment URLs if any
                if message.attachments:
                    message_parts.append(' '.join(attachment.url for attachment in message.attachments))
                
                # Add embed fields if any
                if message.embeds:
                    embed_fields = []
                    for embed in message.embeds:
                        if embed.fields:
                            for field in embed.fields:
                                embed_fields.append(f"{field.name}: {field.value}")
                    if embed_fields:
                        message_parts.append(' '.join(embed_fields))
                
                # Join all parts with a single space
                full_message_content = ' '.join(message_parts)
                if ai_response:
                    full_message_content = f"{full_message_content} {ai_response}".strip()

                # Only process messages that occur after bot start
                if message.created_at >= self.start_time:
                    pass # Placeholder where achievement check used to be

                # Store messages and stats only for primary guild
                if str(message.guild.id) == primary_guild_id:
                    # Log the message in the dashboard ALWAYS for primary guild messages
                    self.dashboard_manager.log_message(message.author, message.guild.name, message.channel.name)
                    
                    conn = await get_db_connection()
                    try:
                        if full_message_content:
                            # Use immediate storage for real-time dashboard updates
                            await store_message(conn, message, full_message_content)
                            await set_last_message_id(conn, message.channel.id, message.id)
                    except Exception as e:
                        logging.error(f"Error storing message: {str(e)}") # Use standard logging
                    finally:
                        await conn.close()

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

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates and tracking."""
        if member.bot:
            return

        # Only process voice updates that occur after bot start
        if discord.utils.utcnow() < self.start_time:
            return

        conn = await get_db_connection()
        try:
            # Handle voice channel changes
            if after.channel is not None and (before.channel is None or before.channel != after.channel):
                # User joined a channel
                await track_voice_join(conn, str(member.id), str(after.channel.id))
                # Removed achievement check for voice join
            elif after.channel is None and before.channel is not None:
                # User left a channel
                await track_voice_leave(conn, str(member.id))
                # Removed achievement check for voice leave
            elif before.channel != after.channel:
                # User switched channels
                await track_voice_leave(conn, str(member.id))
                await track_voice_join(conn, str(member.id), str(after.channel.id))
        except Exception as e:
            logging.error(f"Error tracking voice state: {str(e)}") # Use standard logging
        finally:
            await conn.close()

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
                await flush_message_batches()
                await close_all_pools()
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
