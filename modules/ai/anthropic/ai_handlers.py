from typing import List, Dict, Any, Optional, BinaryIO
import discord
import aiohttp
import io
import base64
import asyncio
from .ai_constants import MAX_MESSAGE_LENGTH, MAX_HISTORY_LENGTH, DEFAULT_CONFIG, FRIENDLY_CONFIG, NOT_FRIENDLY_CONFIG, TEST_INSULTS_CONFIG, TEST_COMPLIMENTS_CONFIG, ERROR_MESSAGES

class MessageHandler:
    @staticmethod
    async def send_split_message(channel: discord.TextChannel, content: str, reply_to: Optional[discord.Message] = None) -> None:
        """Split and send a message that may exceed Discord's length limit."""
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
        """Download a Discord attachment."""
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                return io.BytesIO(data)

    @staticmethod
    async def process_text_attachment(attachment: discord.Attachment) -> str:
        """Process a text file attachment and return its contents."""
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
        """Process an image attachment and return it in Claude's required format."""
        file_content = await AttachmentHandler.download_attachment(attachment)
        if file_content is None:
            return None
        
        image_data = base64.b64encode(file_content.getvalue()).decode('utf-8')
        media_type = attachment.content_type or "image/jpeg"
        
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data
            }
        }

class ConversationManager:
    def __init__(self):
        self.user_conversation_histories: Dict[str, List[Dict[str, str]]] = {}

    def update_history(self, user_id: str, role: str, content: str) -> None:
        """Update the conversation history for a user."""
        if user_id not in self.user_conversation_histories:
            self.user_conversation_histories[user_id] = []
        
        # Use "user" instead of "human" for the user's messages
        if role == "human":
            role = "user"
        
        self.user_conversation_histories[user_id].append({"role": role, "content": content})
        
        # Trim history if it exceeds the maximum length
        if len(self.user_conversation_histories[user_id]) > MAX_HISTORY_LENGTH:
            self.user_conversation_histories[user_id] = self.user_conversation_histories[user_id][-MAX_HISTORY_LENGTH:]

    def clear_history(self, user_id: str) -> None:
        """Clear the conversation history for a user."""
        if user_id in self.user_conversation_histories:
            del self.user_conversation_histories[user_id]

    def get_history(self, user_id: str) -> List[Dict[str, str]]:
        """Get the conversation history for a user."""
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
        
        # Current configuration
        self.random_response_chance = self.default_config.total_chance
        self.insult_weight = self.default_config.insult_weight
        self.compliment_weight = self.default_config.compliment_weight
        
        # Predefined configurations
        self.configs = {
            "default": self.default_config,
            "friendly": ProbabilityConfig(**FRIENDLY_CONFIG),
            "not-friendly": ProbabilityConfig(**NOT_FRIENDLY_CONFIG),
            "test-insults": ProbabilityConfig(**TEST_INSULTS_CONFIG),
            "test-compliments": ProbabilityConfig(**TEST_COMPLIMENTS_CONFIG)
        }
        
        # Timer task
        self.active_timer: Optional[asyncio.Task] = None

    def update_probabilities(self, total_chance: Optional[float] = None, 
                           insult_weight: Optional[float] = None, 
                           compliment_weight: Optional[float] = None) -> None:
        """Update the probability configuration."""
        if total_chance is not None:
            self.random_response_chance = max(0, min(1, total_chance))
        
        if insult_weight is not None and compliment_weight is not None:
            total_weight = insult_weight + compliment_weight
            if total_weight > 0:
                self.insult_weight = insult_weight / total_weight
                self.compliment_weight = compliment_weight / total_weight

    async def reset_to_default(self) -> None:
        """Reset probabilities to default configuration."""
        self.update_probabilities(
            self.default_config.total_chance,
            self.default_config.insult_weight,
            self.default_config.compliment_weight
        )

    async def set_config(self, config_name: str, duration: Optional[int] = None) -> None:
        """Set a predefined configuration with optional duration."""
        if config_name not in self.configs:
            raise ValueError(ERROR_MESSAGES["mode_error"])
            
        config = self.configs[config_name]
        self.update_probabilities(
            config.total_chance,
            config.insult_weight,
            config.compliment_weight
        )
        
        # Cancel any existing timer
        if self.active_timer:
            self.active_timer.cancel()
            self.active_timer = None
            
        # Set up new timer if duration is specified
        if duration:
            self.active_timer = asyncio.create_task(self._config_timer(duration))

    async def _config_timer(self, duration: int) -> None:
        """Internal timer for resetting configuration after duration."""
        await asyncio.sleep(duration)
        await self.reset_to_default()
        self.active_timer = None

    def get_config(self, config_name: str) -> ProbabilityConfig:
        """Get a configuration by name."""
        if config_name not in self.configs:
            raise ValueError(ERROR_MESSAGES["mode_error"])
        return self.configs[config_name]

    def list_configs(self) -> Dict[str, ProbabilityConfig]:
        """Get all available configurations."""
        return self.configs.copy()
