from anthropic import AsyncAnthropic
import discord
import traceback
import random
import re
from typing import List, Dict, Any, Optional
import datetime

from .ai_constants import (
    DEFAULT_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE,
    BRIEF_MAX_TOKENS, BRIEF_TEMPERATURE, TEXT_FILE_EXTENSIONS,
    ERROR_MESSAGES, TRIGGER_PHRASE, TRIGGER_PATTERN,
    ROLE_USER, ROLE_ASSISTANT, CONTENT_TYPE_TEXT, CONTENT_TYPE_IMAGE,
    TOOL_TYPE_WEB_SEARCH, TOOL_NAME_WEB_SEARCH,
    KEY_TYPE, KEY_ROLE, KEY_CONTENT,
    COMMAND_AI_SETMODE, COMMAND_AI_LISTMODES,
    COMMAND_SETMODE_DESC, COMMAND_LISTMODES_DESC,
    LISTMODES_HEADER, LISTMODES_NAME_FORMAT,
    LISTMODES_CHANCE_FORMAT, LISTMODES_RATIO_FORMAT,
    LISTMODES_SEPARATOR
)
from .prompts import (
    SYSTEM_PROMPT, get_insult_prompt,
    get_compliment_prompt, get_mode_change_prompt
)
from .ai_handlers import (
    MessageHandler, AttachmentHandler,
    ConversationManager, ProbabilityManager
)

class AIHandler:
    def __init__(self, bot: discord.Client, anthropic_api_key: str):
        # Initialize the AI handler with required components.
        self.bot = bot
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
        
        # Initialize handlers
        self.message_handler = MessageHandler()
        self.attachment_handler = AttachmentHandler()
        self.conversation_manager = ConversationManager()
        self.probability_manager = ProbabilityManager()

    async def handle_oi_drongo(self, message: discord.Message, full_message_content: str, image_attachments: List[Dict[str, Any]]) -> None:
        # Handle messages starting with trigger phrase
        self.bot.logger.info(f"Handling '{TRIGGER_PHRASE}' message")
        async with message.channel.typing():
            try:
                # Remove trigger phrase from the beginning of the message
                cleaned_content = re.sub(TRIGGER_PATTERN, '', full_message_content, flags=re.IGNORECASE).strip()
                self.bot.logger.info(f"Cleaned content: {cleaned_content}")

                # Construct the message content array with both text and images
                message_content_for_api = []
                message_content_for_api.extend(image_attachments)
                message_content_for_api.append({
                    KEY_TYPE: CONTENT_TYPE_TEXT,
                    "text": cleaned_content
                })
                self.bot.logger.info(f"Message content array for API: {message_content_for_api}")

                # Update conversation history with user's message
                self.conversation_manager.update_history(str(message.author.id), ROLE_USER, cleaned_content)

                # Get conversation history
                conversation = self.conversation_manager.get_history(str(message.author.id))
                messages_for_api = [
                    {KEY_ROLE: entry[KEY_ROLE], KEY_CONTENT: message_content_for_api if i == len(conversation) - 1 else entry[KEY_CONTENT]}
                    for i, entry in enumerate(conversation)
                ]

                # Prepare API call arguments
                api_call_args = {
                    "model": DEFAULT_MODEL,
                    "max_tokens": DEFAULT_MAX_TOKENS,
                    "system": SYSTEM_PROMPT,
                    "messages": messages_for_api,
                    "temperature": DEFAULT_TEMPERATURE,
                    "tools": [{
                        KEY_TYPE: TOOL_TYPE_WEB_SEARCH,
                        "name": TOOL_NAME_WEB_SEARCH,
                        "max_uses": 5
                    }]
                }

                self.bot.logger.info(f"API call: max_tokens={DEFAULT_MAX_TOKENS}, temperature={DEFAULT_TEMPERATURE}")

                # Get response from Claude
                self.bot.logger.info("Sending request to Claude")
                response = await self.anthropic_client.messages.create(**api_call_args)

                # Find the text content from the response, which may include tool use
                claude_response_text = ""
                if response.content:
                    for block in response.content:
                        if block.type == CONTENT_TYPE_TEXT:
                            claude_response_text += block.text

                if not claude_response_text:
                    self.bot.logger.warning("Received empty or non-text response content from API call")
                self.bot.logger.info("Received response from Claude")

                # Update conversation history with Claude's response
                self.conversation_manager.update_history(str(message.author.id), ROLE_ASSISTANT, claude_response_text)

                # Send the split response
                await self.message_handler.send_split_message(message.channel, claude_response_text, reply_to=message)
            except Exception as e:
                error_traceback = traceback.format_exc()
                error_msg = f"""
                                Error in Claude response:
                                Time: {datetime.datetime.now()}
                                Message: {message.content}
                                Author: {message.author} ({message.author.id})
                                Channel: {message.channel} ({message.channel.id})
                                Guild: {message.guild} ({message.guild.id})
                                Error: {str(e)}
                                Traceback:
                                {error_traceback}
                            """
                self.bot.logger.error(error_msg)
                await message.reply(ERROR_MESSAGES["general_error"])

    async def _generate_brief_response(self, message: discord.Message, prompt_text: str, response_type: str) -> str:
        # Helper method to generate brief responses (insults/compliments) with image support
        async with message.channel.typing():
            try:
                # Process any image attachments
                image_attachments = []
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        image_data = await self.attachment_handler.process_image_attachment(attachment)
                        if image_data:
                            image_attachments.append(image_data)

                # Construct message content array with both text and images
                message_content = []
                message_content.extend(image_attachments)
                message_content.append({
                    KEY_TYPE: CONTENT_TYPE_TEXT,
                    "text": prompt_text
                })

                response = await self.anthropic_client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=BRIEF_MAX_TOKENS,
                    messages=[{KEY_ROLE: ROLE_USER, KEY_CONTENT: message_content}],
                    temperature=BRIEF_TEMPERATURE,
                )

                response_text = response.content[0].text.strip()
                await message.reply(response_text)
                return response_text
            except Exception as e:
                error_traceback = traceback.format_exc()
                error_msg = f"""
                                Error generating {response_type}:
                                Time: {datetime.datetime.now()}
                                Message: {message.content}
                                Author: {message.author} ({message.author.id})
                                Channel: {message.channel} ({message.channel.id})
                                Guild: {message.guild} ({message.guild.id})
                                Error: {str(e)}
                                Traceback:
                                {error_traceback}
                            """
                self.bot.logger.error(error_msg)
                return f"Error generating {response_type}: {str(e)}"

    async def generate_insult(self, message: discord.Message, full_message_content: str) -> str:
        # Generate an insult based on the message content and any images
        return await self._generate_brief_response(
            message,
            get_insult_prompt(full_message_content),
            "insult"
        )

    async def generate_compliment(self, message: discord.Message, full_message_content: str) -> str:
        # Generate a compliment based on the message content and any images
        return await self._generate_brief_response(
            message,
            get_compliment_prompt(full_message_content),
            "compliment"
        )

    async def process_message(self, message: discord.Message) -> str:
        # Process a message and generate appropriate responses.
        self.bot.logger.info(f"Processing message: {message.content}")
        
        # Process text attachments
        text_contents = []
        image_attachments = []
        
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(TEXT_FILE_EXTENSIONS):
                content = await self.attachment_handler.process_text_attachment(attachment)
                text_contents.append(f"Content of {attachment.filename}:\n{content}")
            elif attachment.content_type and attachment.content_type.startswith('image/'):
                image_data = await self.attachment_handler.process_image_attachment(attachment)
                if image_data:
                    image_attachments.append(image_data)

        # Check if this is a reply and get the referenced message if it exists
        referenced_content = ""
        if message.reference is not None:
            try:
                reply_message = await message.channel.fetch_message(message.reference.message_id)
                referenced_content = f"Message being replied to: {reply_message.content}\n\n"
            except Exception as fetch_err:
                self.bot.logger.error(f"Failed to fetch referenced message: {fetch_err}")

        # Remove trigger phrase from the beginning of the message
        cleaned_content = re.sub(TRIGGER_PATTERN, '', message.clean_content, flags=re.IGNORECASE).strip()
        full_message_content = f"{referenced_content}{cleaned_content}\n\n{''.join(text_contents)}".strip()

        # Check for trigger phrase
        if message.content.lower().startswith(TRIGGER_PHRASE):
            self.bot.logger.info(f"Detected '{TRIGGER_PHRASE}' trigger")
            await self.handle_oi_drongo(message, full_message_content, image_attachments)
        # Check for random response using configured probabilities
        elif random.random() < self.probability_manager.random_response_chance:
            self.bot.logger.info("Random response triggered")
            # Use weighted random choice for insult vs compliment
            if random.random() < self.probability_manager.insult_weight:
                await self.generate_insult(message, full_message_content)
            else:
                await self.generate_compliment(message, full_message_content)

        return full_message_content

    async def generate_mode_response(self, mode: str, duration: Optional[int] = None) -> str:
        # Generate a response announcing a mode change.
        config = self.probability_manager.get_config(mode)
        try:
            response = await self.anthropic_client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=BRIEF_MAX_TOKENS,
                messages=[{
                    KEY_ROLE: ROLE_USER,
                    KEY_CONTENT: get_mode_change_prompt(
                        mode,
                        config.compliment_weight * 100,
                        config.insult_weight * 100,
                        config.total_chance,
                        duration
                    )
                }],
                temperature=BRIEF_TEMPERATURE,
            )

            return response.content[0].text.strip()
        except Exception as e:
            error_traceback = traceback.format_exc()
            error_msg = f"""
                            Error generating mode change response:
                            Time: {datetime.datetime.now()}
                            Mode: {mode}
                            Duration: {duration}
                            Error: {str(e)}
                            Traceback:
                            {error_traceback}
                        """
            self.bot.logger.error(error_msg)
            return ERROR_MESSAGES["mode_change_error"].format(error=str(e))

    async def setmode_command(self, interaction: discord.Interaction, mode: str, duration: Optional[int] = None) -> None:
        # Set the bot's response mode with optional duration.
        if str(interaction.user.id) != self.bot.authorized_user_id:
            await interaction.response.send_message(ERROR_MESSAGES["unauthorized"], ephemeral=True)
            return

        await interaction.response.defer()

        try:
            await self.probability_manager.set_config(mode, duration)
            response = await self.generate_mode_response(mode, duration)
            await interaction.followup.send(response)
        except ValueError as e:
            error_msg = f"""
                            Error setting mode (ValueError):
                            Time: {datetime.datetime.now()}
                            User: {interaction.user} ({interaction.user.id})
                            Mode: {mode}
                            Duration: {duration}
                            Error: {str(e)}
                        """
            self.bot.logger.error(error_msg)
            await interaction.followup.send(str(e), ephemeral=True)
        except Exception as e:
            error_traceback = traceback.format_exc()
            error_msg = f"""
                            Error setting mode:
                            Time: {datetime.datetime.now()}
                            User: {interaction.user} ({interaction.user.id})
                            Mode: {mode}
                            Duration: {duration}
                            Error: {str(e)}
                            Traceback:
                            {error_traceback}
                        """
            self.bot.logger.error(error_msg)
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    async def listmodes_command(self, interaction: discord.Interaction) -> None:
        # List all available response modes.
        if str(interaction.user.id) != self.bot.authorized_user_id:
            await interaction.response.send_message(ERROR_MESSAGES["unauthorized"], ephemeral=True)
            return

        response = LISTMODES_HEADER
        for name, config in self.probability_manager.list_configs().items():
            response += LISTMODES_NAME_FORMAT.format(name=name)
            response += LISTMODES_CHANCE_FORMAT.format(chance=config.total_chance * 100)
            response += LISTMODES_RATIO_FORMAT.format(
                insult=config.insult_weight * 100,
                compliment=config.compliment_weight * 100
            )
            response += LISTMODES_SEPARATOR
        
        await interaction.response.send_message(response)

def setup(bot: discord.Client) -> None:
    # Set up the AI handler and register commands.
    @bot.tree.command(name=COMMAND_AI_SETMODE, description=COMMAND_SETMODE_DESC)
    async def ai_setmode_command(interaction: discord.Interaction,
                               mode: str,
                               duration: Optional[int] = None) -> None:
        # Set the bot's response mode.
        await bot.ai_handler.setmode_command(interaction, mode, duration)

    @bot.tree.command(name=COMMAND_AI_LISTMODES, description=COMMAND_LISTMODES_DESC)
    async def ai_listmodes_command(interaction: discord.Interaction) -> None:
        # List all available response modes.
        await bot.ai_handler.listmodes_command(interaction)