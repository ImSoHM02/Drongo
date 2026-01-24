from typing import List, Dict, Any, Optional, BinaryIO
import discord
import aiohttp
import io
import base64
import asyncio
from .ai_constants import (
    MAX_MESSAGE_LENGTH, MAX_HISTORY_LENGTH,
    DEFAULT_CONFIG, FRIENDLY_CONFIG, NOT_FRIENDLY_CONFIG,
    TEST_INSULTS_CONFIG, TEST_COMPLIMENTS_CONFIG,
    ERROR_MESSAGES, ROLE_USER, ROLE_HUMAN,
    KEY_TYPE, KEY_ROLE, KEY_CONTENT, KEY_SOURCE, KEY_MEDIA_TYPE, KEY_DATA,
    CONTENT_TYPE_IMAGE, IMAGE_SOURCE_TYPE, DEFAULT_IMAGE_MEDIA_TYPE,
    CONFIG_NAME_DEFAULT, CONFIG_NAME_FRIENDLY, CONFIG_NAME_NOT_FRIENDLY,
    CONFIG_NAME_TEST_INSULTS, CONFIG_NAME_TEST_COMPLIMENTS
)

class MessageHandler:
    @staticmethod
    async def send_split_message(channel: discord.TextChannel, content: str, reply_to: Optional[discord.Message] = None) -> None:
        # Split and send a message that may exceed Discord's length limit
        messages: List[str] = []
        
        while content:
            if len(content) <= MAX_MESSAGE_LENGTH:
                messages.append(content)
                break

            split_index = content.rfind('\n', 0, MAX_MESSAGE_LENGTH)
            if split_index == -1:
                split_index = content.rfind(' ', 0, MAX_MESSAGE_LENGTH)
            if split_index == -1:
                split_index = MAX_MESSAGE_LENGTH

            messages.append(content[:split_index])
            content = content[split_index:].lstrip()

        for i, message_content in enumerate(messages):
            if i == 0 and reply_to:
                await reply_to.reply(message_content)
            else:
                await channel.send(message_content)

class AttachmentHandler:
    @staticmethod
    async def download_attachment(attachment: discord.Attachment) -> Optional[BinaryIO]:
        # Download a Discord attachment
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                return io.BytesIO(data)

    @staticmethod
    async def process_text_attachment(attachment: discord.Attachment) -> str:
        # Process a text file attachment and return its contents
        file_content = await AttachmentHandler.download_attachment(attachment)
        if file_content is None:
            return ERROR_MESSAGES["download_failed"]
        
        try:
            text_content = file_content.getvalue().decode('utf-8')
            return text_content
        except UnicodeDecodeError:
            return ERROR_MESSAGES["decode_failed"]

    @staticmethod
    async def process_image_attachment(attachment: discord.Attachment) -> Optional[Dict[str, Any]]:
        # Process an image attachment and return it in Claude's required format
        file_content = await AttachmentHandler.download_attachment(attachment)
        if file_content is None:
            return None

        image_data = base64.b64encode(file_content.getvalue()).decode('utf-8')
        media_type = attachment.content_type or DEFAULT_IMAGE_MEDIA_TYPE

        return {
            KEY_TYPE: CONTENT_TYPE_IMAGE,
            KEY_SOURCE: {
                KEY_TYPE: IMAGE_SOURCE_TYPE,
                KEY_MEDIA_TYPE: media_type,
                KEY_DATA: image_data
            }
        }

class ConversationManager:
    def __init__(self):
        self.user_conversation_histories: Dict[str, List[Dict[str, str]]] = {}

    def update_history(self, user_id: str, role: str, content: str) -> None:
        # Update the conversation history for a user
        if user_id not in self.user_conversation_histories:
            self.user_conversation_histories[user_id] = []

        # Use "user" instead of "human" for the user's messages
        if role == ROLE_HUMAN:
            role = ROLE_USER

        self.user_conversation_histories[user_id].append({KEY_ROLE: role, KEY_CONTENT: content})
        
        # Trim history if it exceeds the maximum length
        if len(self.user_conversation_histories[user_id]) > MAX_HISTORY_LENGTH:
            self.user_conversation_histories[user_id] = self.user_conversation_histories[user_id][-MAX_HISTORY_LENGTH:]

    def clear_history(self, user_id: str) -> None:
        # Clear the conversation history for a user
        if user_id in self.user_conversation_histories:
            del self.user_conversation_histories[user_id]

    def get_history(self, user_id: str) -> List[Dict[str, str]]:
        # Get the conversation history for a user
        return self.user_conversation_histories.get(user_id, [])

class ProbabilityConfig:
    def __init__(self, name: str, total_chance: float, insult_weight: float, compliment_weight: float):
        self.name = name
        self.total_chance = total_chance
        self.insult_weight = insult_weight
        self.compliment_weight = compliment_weight

class ProbabilityManager:
    def __init__(self):
        # Initialize default configuration
        self.default_config = ProbabilityConfig(**DEFAULT_CONFIG)

        # Predefined configurations
        self.configs = {
            CONFIG_NAME_DEFAULT: self.default_config,
            CONFIG_NAME_FRIENDLY: ProbabilityConfig(**FRIENDLY_CONFIG),
            CONFIG_NAME_NOT_FRIENDLY: ProbabilityConfig(**NOT_FRIENDLY_CONFIG),
            CONFIG_NAME_TEST_INSULTS: ProbabilityConfig(**TEST_INSULTS_CONFIG),
            CONFIG_NAME_TEST_COMPLIMENTS: ProbabilityConfig(**TEST_COMPLIMENTS_CONFIG)
        }

        # Per-guild configuration storage
        # Structure: {guild_id: {"chance": float, "insult": float, "compliment": float}}
        self.guild_configs: Dict[str, Dict[str, float]] = {}

        # Per-guild timer tasks
        self.guild_timers: Dict[str, asyncio.Task] = {}

    def get_guild_config(self, guild_id: str) -> Dict[str, float]:
        # Get configuration for a specific guild, or default if not set
        if guild_id not in self.guild_configs:
            return {
                "chance": self.default_config.total_chance,
                "insult": self.default_config.insult_weight,
                "compliment": self.default_config.compliment_weight
            }
        return self.guild_configs[guild_id]

    def update_probabilities(self, guild_id: str, total_chance: Optional[float] = None,
                           insult_weight: Optional[float] = None,
                           compliment_weight: Optional[float] = None) -> None:
        # Update the probability configuration for a specific guild
        config = self.get_guild_config(guild_id)

        if total_chance is not None:
            config["chance"] = max(0, min(1, total_chance))

        if insult_weight is not None and compliment_weight is not None:
            total_weight = insult_weight + compliment_weight
            if total_weight > 0:
                config["insult"] = insult_weight / total_weight
                config["compliment"] = compliment_weight / total_weight

        self.guild_configs[guild_id] = config

    async def reset_to_default(self, guild_id: str) -> None:
        # Reset probabilities to default configuration for a specific guild
        if guild_id in self.guild_configs:
            del self.guild_configs[guild_id]

    async def set_config(self, guild_id: str, config_name: str, duration: Optional[int] = None) -> None:
        # Set a predefined configuration with optional duration for a specific guild
        if config_name not in self.configs:
            raise ValueError(ERROR_MESSAGES["mode_error"])

        config = self.configs[config_name]
        self.update_probabilities(
            guild_id,
            config.total_chance,
            config.insult_weight,
            config.compliment_weight
        )

        # Cancel any existing timer for this guild
        if guild_id in self.guild_timers:
            self.guild_timers[guild_id].cancel()
            del self.guild_timers[guild_id]

        # Set up new timer if duration is specified
        if duration:
            self.guild_timers[guild_id] = asyncio.create_task(self._config_timer(guild_id, duration))

    def apply_mode(self, guild_id: str, config_name: str) -> None:
        """Apply a configuration without timers (used for persisted settings)."""
        if config_name not in self.configs:
            raise ValueError(ERROR_MESSAGES["mode_error"])
        config = self.configs[config_name]
        self.update_probabilities(
            guild_id,
            config.total_chance,
            config.insult_weight,
            config.compliment_weight
        )

    async def _config_timer(self, guild_id: str, duration: int) -> None:
        # Internal timer for resetting configuration after duration for a specific guild
        await asyncio.sleep(duration)
        await self.reset_to_default(guild_id)
        if guild_id in self.guild_timers:
            del self.guild_timers[guild_id]

    def get_config(self, config_name: str) -> ProbabilityConfig:
        # Get a configuration by name
        if config_name not in self.configs:
            raise ValueError(ERROR_MESSAGES["mode_error"])
        return self.configs[config_name]

    def list_configs(self) -> Dict[str, ProbabilityConfig]:
        # Get all available configurations
        return self.configs.copy()
