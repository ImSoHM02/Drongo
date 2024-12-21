from anthropic import AsyncAnthropic
import discord
import traceback
import random
import re
from typing import List, Dict, Any, Optional
import logging
import datetime

from .ai_constants import (
    DEFAULT_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE,
    BRIEF_MAX_TOKENS, BRIEF_TEMPERATURE, TEXT_FILE_EXTENSIONS,
    ERROR_MESSAGES
)
from .ai_prompt import (
    DEFAULT_SYSTEM_PROMPT, get_insult_prompt,
    get_compliment_prompt, get_mode_change_prompt
)
from .ai_handlers import (
    MessageHandler, AttachmentHandler,
    ConversationManager, ProbabilityManager
)

class AIHandler:
    def __init__(self, bot: discord.Client, anthropic_api_key: str):
        """Initialize the AI handler with required components."""
        self.bot = bot
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
        
        # Initialize handlers
        self.message_handler = MessageHandler()
        self.attachment_handler = AttachmentHandler()
        self.conversation_manager = ConversationManager()
        self.probability_manager = ProbabilityManager()

    async def handle_oi_drongo(self, message: discord.Message, full_message_content: str, image_attachments: List[Dict[str, Any]]) -> None:
        """Handle messages starting with 'oi drongo'."""
        self.bot.logger.info("Handling 'oi drongo' message")
        async with message.channel.typing():
            try:
                # Remove "oi drongo" from the beginning of the message
                cleaned_content = re.sub(r'^oi\s+drongo\s*', '', full_message_content, flags=re.IGNORECASE).strip()
                self.bot.logger.info(f"Cleaned content: {cleaned_content}")

                # Construct the message content array with both text and images
                message_content = []
                message_content.extend(image_attachments)
                if cleaned_content:
                    message_content.append({
                        "type": "text",
                        "text": cleaned_content
                    })
                self.bot.logger.info(f"Message content array: {message_content}")

                # Update conversation history with user's message
                self.conversation_manager.update_history(str(message.author.id), "user", cleaned_content)

                # Get conversation history
                conversation = self.conversation_manager.get_history(str(message.author.id))
                messages = [
                    {"role": entry["role"], "content": message_content if i == len(conversation) - 1 else entry["content"]}
                    for i, entry in enumerate(conversation)
                ]

                # Get response from Claude
                self.bot.logger.info("Sending request to Claude")
                response = await self.anthropic_client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=DEFAULT_MAX_TOKENS,
                    system=DEFAULT_SYSTEM_PROMPT,
                    messages=messages,
                    temperature=DEFAULT_TEMPERATURE,
                )
                self.bot.logger.info("Received response from Claude")

                # Update conversation history with Claude's response
                claude_response = response.content[0].text
                self.conversation_manager.update_history(str(message.author.id), "assistant", claude_response)

                # Send the split response
                await self.message_handler.send_split_message(message.channel, claude_response, reply_to=message)
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
                self.bot.logger.error(f"Error in Claude response: {str(e)}")
                await message.reply(ERROR_MESSAGES["general_error"])

    async def generate_insult(self, message: discord.Message, full_message_content: str) -> str:
        """Generate an insult based on the message content."""
        async with message.channel.typing():
            try:
                response = await self.anthropic_client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=BRIEF_MAX_TOKENS,
                    system=DEFAULT_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": get_insult_prompt(full_message_content)}],
                    temperature=BRIEF_TEMPERATURE,
                )

                insult = response.content[0].text.strip()
                await message.reply(insult)
                return insult
            except Exception as e:
                error_traceback = traceback.format_exc()
                error_msg = f"""
Error generating insult:
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
                self.bot.logger.error(f"Error generating insult: {str(e)}")
                return f"Error generating insult: {str(e)}"

    async def generate_compliment(self, message: discord.Message, full_message_content: str) -> str:
        """Generate a compliment based on the message content."""
        async with message.channel.typing():
            try:
                response = await self.anthropic_client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=BRIEF_MAX_TOKENS,
                    system=DEFAULT_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": get_compliment_prompt(full_message_content)}],
                    temperature=BRIEF_TEMPERATURE,
                )

                compliment = response.content[0].text.strip()
                await message.reply(compliment)
                return compliment
            except Exception as e:
                error_traceback = traceback.format_exc()
                error_msg = f"""
Error generating compliment:
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
                self.bot.logger.error(f"Error generating compliment: {str(e)}")
                return f"Error generating compliment: {str(e)}"

    async def process_message(self, message: discord.Message) -> str:
        """Process a message and generate appropriate responses."""
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

        # Remove "oi drongo" from the beginning of the message
        cleaned_content = re.sub(r'^oi\s+drongo\s*', '', message.clean_content, flags=re.IGNORECASE).strip()
        full_message_content = f"{cleaned_content}\n\n{''.join(text_contents)}".strip()

        # Check for "oi drongo" trigger
        if message.content.lower().startswith("oi drongo"):
            self.bot.logger.info("Detected 'oi drongo' trigger")
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
        """Generate a response announcing a mode change."""
        config = self.probability_manager.get_config(mode)
        try:
            response = await self.anthropic_client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=BRIEF_MAX_TOKENS,
                system=DEFAULT_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": get_mode_change_prompt(
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
            self.bot.logger.error(f"Error generating mode change response: {str(e)}")
            return ERROR_MESSAGES["mode_change_error"].format(error=str(e))

    async def setmode_command(self, interaction: discord.Interaction, mode: str, duration: Optional[int] = None) -> None:
        """Set the bot's response mode with optional duration."""
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
            self.bot.logger.error(f"Error setting mode: {str(e)}")
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
            self.bot.logger.error(f"Error setting mode: {str(e)}")
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    async def listmodes_command(self, interaction: discord.Interaction) -> None:
        """List all available response modes."""
        if str(interaction.user.id) != self.bot.authorized_user_id:
            await interaction.response.send_message(ERROR_MESSAGES["unauthorized"], ephemeral=True)
            return

        response = "**Eshay bah! Here's all me different moods ay:**\n"
        for name, config in self.probability_manager.list_configs().items():
            response += f"\n**{name}**"
            response += f"\n- Chance of me poppin' off: {config.total_chance * 100:.1f}%"
            response += f"\n- Ratio of insults to compliments: {config.insult_weight * 100:.0f}/{config.compliment_weight * 100:.0f}"
            response += "\n- - - - - - - - - -"
        
        await interaction.response.send_message(response)

def setup(bot: discord.Client) -> None:
    """Set up the AI handler and register commands."""
    @bot.tree.command(name="setmode", description="Set the bot's response mode")
    async def setmode_command(interaction: discord.Interaction, 
                            mode: str, 
                            duration: Optional[int] = None) -> None:
        """Set the bot's response mode."""
        await bot.ai_handler.setmode_command(interaction, mode, duration)

    @bot.tree.command(name="listmodes", description="List all available response modes")
    async def listmodes_command(interaction: discord.Interaction) -> None:
        """List all available response modes."""
        await bot.ai_handler.listmodes_command(interaction)
