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
                      create_game_tracker_tables)
from dotenv import load_dotenv
from modules import (message_stats, message_management, wordcount, 
                    clearchat, wordrank, emoji_downloader, web_link)
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
        self.heartbeat_timeout = 10  # seconds
        self.heartbeat_task = None
        self.reconnecting = False

    async def heartbeat(self):
        while not self.is_closed():
            if self.ws is not None and self.ws.open:
                await self.ws.ping()
            await asyncio.sleep(self.heartbeat_timeout)

    async def on_connect(self):
        self.heartbeat_task = self.loop.create_task(self.heartbeat())

    async def on_disconnect(self):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
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
        self.achievement_system = AchievementSystem()  # Initialize achievement system

    async def setup_hook(self):
        self.stats_display.start()

    async def on_ready(self):
        self.stats_display.set_status("Connected")
        self.reconnect_attempts = 0
        self.logger.info(f'Logged in as {self.user}')
        await self.setup_bot()

    async def on_disconnect(self):
        self.stats_display.set_status("Disconnected")
        self.logger.warning("Bot disconnected")
        if not self.client.reconnecting:
            self.client.reconnecting = True
            await self.attempt_reconnect()

    async def on_resumed(self):
        self.stats_display.set_status("Connected")
        self.client.reconnecting = False
        self.logger.info("Bot reconnected")

    async def attempt_reconnect(self):
        while self.reconnect_attempts < self.max_reconnect_attempts:
            await self.client.connect(reconnect=True)
            break
        else:
            self.stats_display.log_event("Max reconnection attempts reached. Please restart the bot manually.")

    async def setup_bot(self):
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
                            if message.author != self.user and not message.author.bot:
                                attachment_urls = ' '.join([attachment.url for attachment in message.attachments])
                                full_message_content = f"{message.clean_content} {attachment_urls}".strip()
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
            self.ai_handler = AIHandler(self, self.anthropic_api_key)
            emoji_downloader.setup(self)
            # Web interface command
            web_link.setup(self)
            
            # Load version tracker after AI handler is initialized
            await self.load_extension("modules.version_tracker")
            
            self.logger.info("Loaded all command modules.")

        finally:
            await conn.close()

    async def on_message(self, message):
        if message.author == self.user or message.author.bot:
            return

        # Update message count
        self.stats_display.update_stats("Messages Processed", self.stats_display.stats["Messages Processed"] + 1)

        # Only process messages from the primary guild for AI and database storage
        if str(message.guild.id) == primary_guild_id:
            # Process AI response
            full_message_content = await self.ai_handler.process_message(message)
            
            # Check for achievements
            await self.achievement_system.check_achievement(message)

            conn = await get_db_connection()
            try:
                if full_message_content:
                    await store_message(conn, message, full_message_content)
                    await set_last_message_id(conn, message.channel.id, message.id)
                    
                    # Log the message in the stats display
                    self.stats_display.log_message(message.author, message.guild.name, message.channel.name)

            finally:
                await conn.close()

        await self.process_commands(message)

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

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
