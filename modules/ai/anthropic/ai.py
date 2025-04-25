from anthropic import AsyncAnthropic
import discord
import traceback
import random
import re
from typing import List, Dict, Any, Optional
import datetime
import logging # Import standard logging

from .ai_constants import (
    DEFAULT_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE,
    BRIEF_MAX_TOKENS, BRIEF_TEMPERATURE, TEXT_FILE_EXTENSIONS,
    ERROR_MESSAGES, EXTENDED_THINKING_BUDGET, # Added import
    EXTENDED_OUTPUT_MAX_TOKENS, EXTENDED_OUTPUT_BETA_FLAG # Added imports for 128k beta
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
        # Handle messages starting with 'oi drongo'.
        self.bot.logger.info("Handling 'oi drongo' message")
        async with message.channel.typing():
            try:
                # Remove "oi drongo" from the beginning of the message
                cleaned_content = re.sub(r'^oi\s+drongo\s*', '', full_message_content, flags=re.IGNORECASE).strip()
                self.bot.logger.info(f"Cleaned content: {cleaned_content}")

                # Check for extended thinking trigger
                thinking_params = None
                if "{extended_think}" in cleaned_content:
                    cleaned_content = cleaned_content.replace("{extended_think}", "").strip()
                    thinking_params = {
                        "type": "enabled",
                        "budget_tokens": EXTENDED_THINKING_BUDGET
                    }
                    self.bot.logger.info("Extended thinking enabled for this request.")

                # Construct the message content array with both text and images
                message_content_for_api = []
                message_content_for_api.extend(image_attachments)
                # Always include the potentially modified full message content for the API
                # Note: We use the *original* full_message_content here which might still contain the trigger
                # if we want the AI to potentially see it, though it's removed from history.
                # Alternatively, use the cleaned_content if the trigger should be hidden from the AI.
                # For now, let's use the original full_message_content.
                message_content_for_api.append({
                    "type": "text",
                    "text": full_message_content # Using original content for API context
                })
                self.bot.logger.info(f"Message content array for API: {message_content_for_api}")

                # Update conversation history with user's message (using content *without* the trigger)
                self.conversation_manager.update_history(str(message.author.id), "user", cleaned_content)

                # Get conversation history
                conversation = self.conversation_manager.get_history(str(message.author.id))
                messages_for_api = [
                    {"role": entry["role"], "content": message_content_for_api if i == len(conversation) - 1 else entry["content"]}
                    for i, entry in enumerate(conversation)
                ]

                # Prepare API call arguments
                api_call_args = {
                    "model": DEFAULT_MODEL,
                    "max_tokens": DEFAULT_MAX_TOKENS,
                    "system": SYSTEM_PROMPT,
                    "messages": messages_for_api,
                    "temperature": DEFAULT_TEMPERATURE,
                }

                # Add thinking/beta parameters if enabled, remove incompatible ones
                if thinking_params:
                    api_call_args["thinking"] = thinking_params
                    api_call_args["max_tokens"] = EXTENDED_OUTPUT_MAX_TOKENS
                    api_call_args["betas"] = [EXTENDED_OUTPUT_BETA_FLAG]
                    # Remove temperature as it's incompatible with thinking
                    if "temperature" in api_call_args:
                        del api_call_args["temperature"]
                    self.bot.logger.info(f"Extended thinking enabled: budget={EXTENDED_THINKING_BUDGET}, max_tokens={EXTENDED_OUTPUT_MAX_TOKENS}, betas={api_call_args['betas']}")
                else:
                    # Ensure default temperature is present for standard calls
                    api_call_args["temperature"] = DEFAULT_TEMPERATURE
                    self.bot.logger.info(f"Standard call: max_tokens={DEFAULT_MAX_TOKENS}, temperature={DEFAULT_TEMPERATURE}")

                # Get response from Claude using the standard client
                # Beta features are activated via parameters in api_call_args
                self.bot.logger.info("Sending request to Claude via standard messages.create")
                response = await self.anthropic_client.messages.create(**api_call_args)
                self.bot.logger.info("Received response from Claude")

                # Update conversation history with Claude's response
                claude_response = response.content[0].text
                self.conversation_manager.update_history(str(message.author.id), "assistant", claude_response)

                # Send the split response
                await self.message_handler.send_split_message(message.channel, claude_response, reply_to=message)
            except Exception as e:
                # Determine context for error logging
                error_context_title = "Error in Claude response (Extended Thinking / Beta)" if use_beta_client else "Error in Claude response (Standard)"
                
                error_traceback = traceback.format_exc()
                error_msg = f"""
                                {error_context_title}:
                                Time: {datetime.datetime.now()}
                                Message: {message.content}
                                Author: {message.author} ({message.author.id})
                                Channel: {message.channel} ({message.channel.id})
                                Guild: {message.guild} ({message.guild.id})
                                Error: {str(e)}
                                Traceback:
                                {error_traceback}
                            """
                # Log the detailed error message using standard logging
                logging.error(error_msg)
                # Send a generic error reply to the user
                await message.reply(ERROR_MESSAGES["general_error"])

    async def generate_insult(self, message: discord.Message, full_message_content: str) -> str:
        # Generate an insult based on the message content and any images.
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
                    "type": "text",
                    "text": get_insult_prompt(full_message_content)
                })

                response = await self.anthropic_client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=BRIEF_MAX_TOKENS,
                    messages=[{"role": "user", "content": message_content}],
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
                logging.error(error_msg) # Use standard logging
                # self.bot.logger.error(f"Error generating insult: {str(e)}") # Redundant logging removed
                return f"Error generating insult: {str(e)}"

    async def generate_compliment(self, message: discord.Message, full_message_content: str) -> str:
        # Generate a compliment based on the message content and any images.
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
                    "type": "text",
                    "text": get_compliment_prompt(full_message_content)
                })

                response = await self.anthropic_client.messages.create(
                    model=DEFAULT_MODEL,
                    max_tokens=BRIEF_MAX_TOKENS,
                    messages=[{"role": "user", "content": message_content}],
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
                logging.error(error_msg) # Use standard logging
                # self.bot.logger.error(f"Error generating compliment: {str(e)}") # Redundant logging removed
                return f"Error generating compliment: {str(e)}"

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
            except Exception as fetch_err: # Catch specific exception
                logging.error(f"Failed to fetch referenced message: {fetch_err}") # Use standard logging

        # Remove "oi drongo" from the beginning of the message
        cleaned_content = re.sub(r'^oi\s+drongo\s*', '', message.clean_content, flags=re.IGNORECASE).strip()
        full_message_content = f"{referenced_content}{cleaned_content}\n\n{''.join(text_contents)}".strip()

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
        # Generate a response announcing a mode change.
        config = self.probability_manager.get_config(mode)
        try:
            response = await self.anthropic_client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=BRIEF_MAX_TOKENS,
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
            logging.error(error_msg) # Use standard logging
            # self.bot.logger.error(f"Error generating mode change response: {str(e)}") # Redundant logging removed
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
            logging.error(error_msg) # Use standard logging
            # self.bot.logger.error(f"Error setting mode: {str(e)}") # Redundant logging removed
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
            logging.error(error_msg) # Use standard logging
            # self.bot.logger.error(f"Error setting mode: {str(e)}") # Redundant logging removed
            await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)

    async def listmodes_command(self, interaction: discord.Interaction) -> None:
        # List all available response modes.
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
    # Set up the AI handler and register commands.
    @bot.tree.command(name="ai_setmode", description="Set the bot's response mode")
    async def ai_setmode_command(interaction: discord.Interaction, 
                               mode: str, 
                               duration: Optional[int] = None) -> None:
        # Set the bot's response mode.
        await bot.ai_handler.setmode_command(interaction, mode, duration)

    @bot.tree.command(name="ai_listmodes", description="List all available response modes")
    async def ai_listmodes_command(interaction: discord.Interaction) -> None:
        # List all available response modes.
        await bot.ai_handler.listmodes_command(interaction)