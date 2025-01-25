import discord
import os
import logging
import signal
import sys
import asyncio
from rich.logging import RichHandler
from rich.console import Console
from discord.ext import commands
from database import (create_table, store_message, get_db_connection, 
                      set_last_message_id, get_last_message_id,
                      create_game_tracker_tables, track_voice_join,
                      track_voice_leave, get_user_voice_stats,
                      get_voice_leaderboard)
import command_database
from dotenv import load_dotenv
from modules import (message_stats, message_management, wordcount,
                     clearchat, wordrank, emoji_downloader, web_link,
                     steam_commands)
from modules.achievements import AchievementSystem
from modules.stats_display import StatsDisplay
from discord import Client
from modules.ai import AIHandler

console = Console()

# Set up logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler for error.log
file_handler = logging.FileHandler('logs/error.log')
file_handler.setLevel(logging.INFO)  # Changed to INFO to capture all logs
file_handler.setFormatter(log_formatter)

# Rich console handler
console_handler = RichHandler()
console_handler.setLevel(logging.INFO)  # Changed to INFO to capture all logs

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)  # Changed to INFO to capture all logs
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Set logging level for noisy modules
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Custom logger that only logs to the stats display
class StatsLogger:
    def __init__(self, stats_display):
        self.stats_display = stats_display

    def info(self, msg):
        self.stats_display.log_event(f"INFO: {msg}")

    def warning(self, msg):
        self.stats_display.log_event(f"WARNING: {msg}")

    def error(self, msg):
        self.stats_display.log_event(f"ERROR: {msg}")

load_dotenv('id.env')

token = os.getenv("DISCORD_BOT_TOKEN")
client_id = os.getenv("DISCORD_CLIENT_ID")
primary_guild_id = os.getenv("DISCORD_GUILD_ID").split(',')[0].strip()  # Get first guild ID for logging
authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
my_user_id = os.getenv("BLACKTHENWHITE_USER_ID")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")

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
        self.stats_display = StatsDisplay(console)
        self.logger = StatsLogger(self.stats_display)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.anthropic_api_key = anthropic_api_key
        self.ai_handler = None  # Initialize ai_handler as None
        self.achievement_system = AchievementSystem(self)  # Initialize achievement system with bot instance
        self.start_time = None  # Will be set when bot is ready

    async def setup_hook(self):
        self.stats_display.start()

    async def on_ready(self):
        self.stats_display.set_status("Connected")
        self.reconnect_attempts = 0
        self.logger.info(f'Logged in as {self.user}')
        self.start_time = discord.utils.utcnow()  # Set bot start time
        await self.setup_bot()

    async def on_disconnect(self):
        self.stats_display.set_status("Disconnected")
        self.logger.warning("Bot disconnected")
        # Don't attempt reconnect here - let Discord.py handle initial reconnection
        if not self.is_closed():
            try:
                await asyncio.sleep(5)  # Wait before checking connection
                if not self.is_ws_ratelimited() and not self.ws:
                    await self.attempt_reconnect()
            except Exception as e:
                self.logger.error(f"Error during disconnect handling: {e}")

    async def on_resumed(self):
        self.stats_display.set_status("Connected")
        self.reconnect_attempts = 0  # Reset reconnect attempts on successful reconnection
        self.logger.info("Bot reconnected")
        # Verify connection is stable
        try:
            if self.ws and self.ws.open:
                self.logger.info("Connection verified stable")
            else:
                self.logger.warning("Connection may be unstable")
        except Exception as e:
            self.logger.error(f"Error checking connection stability: {e}")

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
                self.logger.error(f"Reconnection attempt failed: {str(e)}")
                # Add exponential backoff
                await asyncio.sleep(min(2 ** self.reconnect_attempts, 60))
        else:
            self.logger.error("Max reconnection attempts reached. Please restart the bot manually.")

    async def setup_bot(self):
        # Initialize command stats database first
        cmd_conn = await command_database.db_connect()
        try:
            await command_database.create_tables(cmd_conn)
        finally:
            await cmd_conn.close()

        # Initialize main database
        conn = await get_db_connection()
        try:
            await create_table(conn)
            await create_game_tracker_tables(conn)
            await self.load_extension("modules.restart")
            self.logger.info('Processing chat messages...')
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

            self.logger.info("Finished processing all channels.")

            # Set up commands from modules
            message_stats.setup(self)
            message_management.setup(self)
            wordcount.setup(self)
            clearchat.setup(self)
            wordrank.setup(self)
            
            # Initialize and set up AI handler
            self.ai_handler = AIHandler(self, self.anthropic_api_key)
            from modules.ai.anthropic import ai
            ai.setup(self)
            
            emoji_downloader.setup(self)
            # Web interface command
            web_link.setup(self)
            # Achievement commands
            from modules import achievement_commands
            achievement_commands.setup(self)
            
            # Steam commands
            steam_commands.setup(self)
            
            # Load version tracker after AI handler is initialized
            await self.load_extension("modules.version_tracker")
            
            self.logger.info("Loaded all command modules.")

        finally:
            await conn.close()

    async def on_interaction(self, interaction):
        """Track slash command usage."""
        try:
            if interaction.type == discord.InteractionType.application_command:
                cmd_conn = await command_database.db_connect()
                try:
                    await command_database.update_command_stats(cmd_conn, str(interaction.user.id), interaction.command.name)
                except Exception as e:
                    self.logger.error(f"Error updating command stats: {str(e)}")
                finally:
                    await cmd_conn.close()
            # Let discord.py's command system handle the interaction
            await self.process_application_commands(interaction)
        except Exception as e:
            self.logger.error(f"Error processing interaction: {str(e)}")

    async def on_message(self, message):
        try:
            if message.author == self.user:  # Only exclude our own messages
                return

            # Update message count
            self.stats_display.update_stats("Messages Processed", self.stats_display.stats["Messages Processed"] + 1)

            # Process AI response for all guilds if ai_handler is initialized
            ai_response = None
            if self.ai_handler is not None:
                try:
                    ai_response = await self.ai_handler.process_message(message)
                except Exception as e:
                    self.logger.error(f"Error processing AI message: {str(e)}")

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
                    try:
                        await self.achievement_system.check_achievement(message)
                    except Exception as e:
                        self.logger.error(f"Error checking achievements: {str(e)}")

                # Store messages and stats only for primary guild
                if str(message.guild.id) == primary_guild_id:
                    conn = await get_db_connection()
                    try:
                        if full_message_content:
                            await store_message(conn, message, full_message_content)
                            await set_last_message_id(conn, message.channel.id, message.id)
                            
                            # Log the message in the stats display
                            self.stats_display.log_message(message.author, message.guild.name, message.channel.name)
                    except Exception as e:
                        self.logger.error(f"Error storing message: {str(e)}")
                    finally:
                        await conn.close()

                # Track command usage in separate database
                if message.content.startswith(('/', '!')):  # Track both slash and ! commands
                    command_text = message.content[1:]  # Remove the prefix (/ or !)
                    command_name = command_text.split()[0]  # Get just the command name
                    cmd_conn = await command_database.db_connect()
                    try:
                        await command_database.update_command_stats(cmd_conn, str(message.author.id), command_name)
                    except Exception as e:
                        self.logger.error(f"Error updating command stats: {str(e)}")
                    finally:
                        await cmd_conn.close()
                
                # Track "oi drongo" usage in separate database
                elif message.content.lower().startswith('oi drongo'):
                    cmd_conn = await command_database.db_connect()
                    try:
                        await command_database.update_command_stats(cmd_conn, str(message.author.id), 'oi_drongo')
                    except Exception as e:
                        self.logger.error(f"Error updating command stats: {str(e)}")
                    finally:
                        await cmd_conn.close()
                
                await self.process_commands(message)
            except Exception as e:
                self.logger.error(f"Error processing message content: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unhandled error in message processing: {str(e)}")

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
        await self.achievement_system.check_achievement(message, reaction)

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
                await self.achievement_system.check_achievement(voice_state=after, member=member)
            elif after.channel is None and before.channel is not None:
                # User left a channel
                await track_voice_leave(conn, str(member.id))
                await self.achievement_system.check_achievement(voice_state=after, member=member)
            elif before.channel != after.channel:
                # User switched channels
                await track_voice_leave(conn, str(member.id))
                await track_voice_join(conn, str(member.id), str(after.channel.id))
        except Exception as e:
            self.logger.error(f"Error tracking voice state: {str(e)}")
        finally:
            await conn.close()

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
intents.members = True
intents.guilds = True

bot = DrongoBot(command_prefix='!', intents=intents)
bot.authorized_user_id = authorized_user_id

def signal_handler(sig, frame):
    bot.stats_display.set_status("Shutting down")
    bot.stats_display.stop()
    # Perform any other necessary cleanup
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    async with bot:
        await bot.setup_hook()
        await bot.start(token)

asyncio.run(main())
