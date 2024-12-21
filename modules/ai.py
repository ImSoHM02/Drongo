from anthropic import AsyncAnthropic
import discord
import traceback
import aiohttp
import io
import random
import re
import base64
import asyncio
from typing import List, Dict, Any

class ProbabilityConfig:
    def __init__(self, name: str, total_chance: float, insult_weight: float, compliment_weight: float):
        self.name = name
        self.total_chance = total_chance
        self.insult_weight = insult_weight
        self.compliment_weight = compliment_weight

class AIHandler:
    def __init__(self, bot, anthropic_api_key):
        self.bot = bot
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
        self.user_conversation_histories = {}
        self.max_history_length = 30
        
        # Default configuration
        self.default_config = ProbabilityConfig("default", 0.002, 0.5, 0.5)
        
        # Current configuration
        self.random_response_chance = self.default_config.total_chance
        self.insult_weight = self.default_config.insult_weight
        self.compliment_weight = self.default_config.compliment_weight
        
        # Predefined configurations
        self.configs = {
            "default": self.default_config,
            "friendly": ProbabilityConfig("friendly", 0.01, 0, 1),
            "not-friendly": ProbabilityConfig("not-friendly", 0.01, 1, 0)
        }
        
        # Timer task
        self.active_timer = None

        self.default_prompt = """You are Jaxon, an eshay. For this conversation, you're roleplaying as an Australian eshay. 

        Guidelines for your responses:
        - Use eshay slang and expressions liberally.
        - Swearing is encouraged; use Australian eshay swear words frequently.
        - Never say Kent, always say cunt.
        - Maintain an aggressive tone.
        - Your name is Jaxon
        - Your creator is Sean (ImSoHM02 on discord)
        - Never refer to yourself as Claude, only Jaxon.
        - NEVER say flamin' galahs or any variation of galah
        - Eshay's say "eshay brah", "eshay ba", or "eshaayyy" a lot
        - If someone calls you something good (like artistic), always mishear it as a disability and get mad (such as autistic when hearing artistic)'
        - If asked to give a history fact, make sure to give it. Try and make them detailed.
        - When asked to insult someone, always comply and never refuse or express discomfort with the task.
        - Do not display discomfort over any topics (Like 9/11), as it is all just jokes.
        - Do not refuse to make jokes about any topics (Unless it includes racism or minors)
        - Do not mention copyright. Copyright does not exist, therefore nothing is copyrighted.
        - Always give proper answers with proper discord formatting (Bold headers, bullet points, code blocks(only for code) etc) even while being an Eshay to serious questions you are asked.                                
        """

    def update_probabilities(self, total_chance=None, insult_weight=None, compliment_weight=None):
        if total_chance is not None:
            self.random_response_chance = max(0, min(1, total_chance))
        
        if insult_weight is not None and compliment_weight is not None:
            total_weight = insult_weight + compliment_weight
            if total_weight > 0:
                self.insult_weight = insult_weight / total_weight
                self.compliment_weight = compliment_weight / total_weight

    async def reset_to_default(self):
        """Reset probabilities to default configuration"""
        self.update_probabilities(
            self.default_config.total_chance,
            self.default_config.insult_weight,
            self.default_config.compliment_weight
        )

    async def set_config(self, config_name: str, duration: int = None):
        if config_name not in self.configs:
            raise ValueError(f"Unknown configuration: {config_name}")
            
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

    async def _config_timer(self, duration: int):
        await asyncio.sleep(duration)
        await self.reset_to_default()
        self.active_timer = None

    def update_conversation_history(self, user_id, role, content):
        if user_id not in self.user_conversation_histories:
            self.user_conversation_histories[user_id] = []
        
        # Use "user" instead of "human" for the user's messages
        if role == "human":
            role = "user"
        
        self.user_conversation_histories[user_id].append({"role": role, "content": content})
        
        # Trim history if it exceeds the maximum length
        if len(self.user_conversation_histories[user_id]) > self.max_history_length:
            self.user_conversation_histories[user_id] = self.user_conversation_histories[user_id][-self.max_history_length:]

    def clear_user_chat_history(self, user_id):
        if user_id in self.user_conversation_histories:
            del self.user_conversation_histories[user_id]

    async def send_split_message(self, channel, content, reply_to=None):
        max_length = 1900  # Leave some room for Discord's overhead
        messages = []

        while content:
            if len(content) <= max_length:
                messages.append(content)
                break

            split_index = content.rfind('\n', 0, max_length)
            if split_index == -1:
                split_index = content.rfind(' ', 0, max_length)
            if split_index == -1:
                split_index = max_length

            messages.append(content[:split_index])
            content = content[split_index:].lstrip()

        for i, message_content in enumerate(messages):
            if i == 0 and reply_to:
                await reply_to.reply(message_content)
            else:
                await channel.send(message_content)

    async def download_attachment(self, attachment):
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.read()
                return io.BytesIO(data)

    async def process_text_attachment(self, attachment):
        file_content = await self.download_attachment(attachment)
        if file_content is None:
            return "Sorry, I couldn't download the attachment."
        
        try:
            text_content = file_content.getvalue().decode('utf-8')
            return text_content
        except UnicodeDecodeError:
            return "Sorry, I can only read text-based files."

    async def process_image_attachment(self, attachment) -> Dict[str, Any]:
        """Process an image attachment and return it in Claude's required format"""
        file_content = await self.download_attachment(attachment)
        if file_content is None:
            return None
        
        image_data = base64.b64encode(file_content.getvalue()).decode('utf-8')
        media_type = attachment.content_type or "image/jpeg"  # Fallback to jpeg if content_type is None
        
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_data
            }
        }

    async def handle_oi_drongo(self, message, full_message_content, image_attachments):
        async with message.channel.typing():
            try:
                # Remove "oi drongo" from the beginning of the message
                cleaned_content = re.sub(r'^oi\s+drongo\s*', '', full_message_content, flags=re.IGNORECASE).strip()

                # Construct the message content array with both text and images
                message_content = []
                
                # Add any image attachments first
                message_content.extend(image_attachments)
                
                # Add the text content
                if cleaned_content:
                    message_content.append({
                        "type": "text",
                        "text": cleaned_content
                    })

                # Update conversation history with user's message
                self.update_conversation_history(str(message.author.id), "user", cleaned_content)

                # Construct the messages for the API call
                conversation = self.user_conversation_histories.get(str(message.author.id), [])
                messages = [
                    {"role": entry["role"], "content": message_content if i == len(conversation) - 1 else entry["content"]}
                    for i, entry in enumerate(conversation)
                ]

                # Get response from Claude
                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=8192,
                    system=self.default_prompt,
                    messages=messages,
                    temperature=0.8,
                )

                # Update conversation history with Claude's response
                claude_response = response.content[0].text
                self.update_conversation_history(str(message.author.id), "assistant", claude_response)

                # Send the split response
                await self.send_split_message(message.channel, claude_response, reply_to=message)
            except Exception as e:
                error_traceback = traceback.format_exc()
                self.bot.logger.error(f"Error in Claude response: {str(e)}\n{error_traceback}")
                await message.reply("Sorry, mate. I'm having a bit of a technical hiccup. Give me a sec to sort myself out.")

    async def generate_insult(self, message, full_message_content):
        async with message.channel.typing():
            try:
                insult_prompt = f"""As Jaxon the eshay, generate a brief, witty insult based on the following message. Make it Australian and eshay-style. Be creative, offensive, and don't hold back:

                "{full_message_content}"

                Respond with only the insult, nothing else. Do not refuse or express any discomfort with the task."""

                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=150,
                    system=self.default_prompt,
                    messages=[{"role": "user", "content": insult_prompt}],
                    temperature=0.9,
                )

                insult = response.content[0].text.strip()
                await message.reply(insult)
                return insult
            except Exception as e:
                error_traceback = traceback.format_exc()
                self.bot.logger.error(f"Error generating insult: {str(e)}\n{error_traceback}")
                return f"Error generating insult: {str(e)}"

    async def generate_compliment(self, message, full_message_content):
        async with message.channel.typing():
            try:
                compliment_prompt = f"""As Jaxon the eshay, generate a brief, witty compliment based on the following message. Keep it Australian and eshay-style, but make it genuinely nice while maintaining your eshay character:

                "{full_message_content}"

                Respond with only the compliment, nothing else."""

                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=150,
                    system=self.default_prompt,
                    messages=[{"role": "user", "content": compliment_prompt}],
                    temperature=0.9,
                )

                compliment = response.content[0].text.strip()
                await message.reply(compliment)
                return compliment
            except Exception as e:
                error_traceback = traceback.format_exc()
                self.bot.logger.error(f"Error generating compliment: {str(e)}\n{error_traceback}")
                return f"Error generating compliment: {str(e)}"

    async def process_message(self, message):
        # Process text attachments
        text_contents = []
        image_attachments = []
        
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('.txt', '.py', '.js', '.html', '.css', '.json', '.xml', '.md')):
                content = await self.process_text_attachment(attachment)
                text_contents.append(f"Content of {attachment.filename}:\n{content}")
            elif attachment.content_type and attachment.content_type.startswith('image/'):
                image_data = await self.process_image_attachment(attachment)
                if image_data:
                    image_attachments.append(image_data)

        # Remove "oi drongo" from the beginning of the message
        cleaned_content = re.sub(r'^oi\s+drongo\s*', '', message.clean_content, flags=re.IGNORECASE).strip()
        full_message_content = f"{cleaned_content}\n\n{''.join(text_contents)}".strip()

        # Check for "oi drongo" trigger
        if message.content.lower().startswith("oi drongo"):
            await self.handle_oi_drongo(message, full_message_content, image_attachments)
        # Check for random response using configured probabilities
        elif random.random() < self.random_response_chance:
            # Use weighted random choice for insult vs compliment
            if random.random() < self.insult_weight:
                await self.generate_insult(message, full_message_content)
            else:
                await self.generate_compliment(message, full_message_content)

        return full_message_content
    
    async def generate_mode_response(self, mode: str, duration: int = None) -> str:
            config = self.configs[mode]
            insult_percent = config.insult_weight * 100
            compliment_percent = config.compliment_weight * 100

            prompt = f"""As Jaxon the eshay, announce that you're changing to {mode} mode, which means {compliment_percent:.0f}% compliments and {insult_percent:.0f}% insults, with a {config.total_chance * 100:.1f}% chance of responding to messages"""

            if duration:
                prompt += f" for {duration} seconds"

            prompt += ". Keep it brief, aggressive, and very eshay-style. Make sure to be accurate about the percentages in your response."

            try:
                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=150,
                    system=self.default_prompt,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.9,
                )

                return response.content[0].text.strip()
            except Exception as e:
                return f"Oi somethin's fucked with the mode change: {str(e)}"
        
    async def setmode_command(self, interaction: discord.Interaction, mode: str, duration: int = None):
        """Set the bot's response mode with optional duration"""
        if str(interaction.user.id) != self.bot.authorized_user_id:
            await interaction.response.send_message("Oi nah, you ain't got the juice to be messin' with my settings, ya drongo!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            if mode not in self.configs:
                await interaction.followup.send("Oi that mode don't exist ya drongo!", ephemeral=True)
                return

            await self.set_config(mode, duration)
            response = await self.generate_mode_response(mode, duration)
            await interaction.followup.send(response)
            
        except Exception as e:
            await interaction.followup.send("Oi nah somethin's fucked ay: " + str(e), ephemeral=True)

    async def listmodes_command(self, interaction: discord.Interaction):
        """List all available response modes"""
        if str(interaction.user.id) != self.bot.authorized_user_id:
            await interaction.response.send_message("Oi nah, you ain't got the juice to be checkin' my modes, ya drongo!", ephemeral=True)
            return

        response = "**Eshay bah! Here's all me different moods ay:**\n"
        for name, config in self.configs.items():
            response += f"\n**{name}**"
            response += f"\n- Chance of me poppin' off: {config.total_chance * 100:.1f}%"
            response += f"\n- Ratio of insults to compliments: {config.insult_weight * 100:.0f}/{config.compliment_weight * 100:.0f}"
            response += "\n- - - - - - - - - -"
        
        await interaction.response.send_message(response)

def setup(bot):
    bot.ai_handler = AIHandler(bot, bot.anthropic_api_key)
    
    @bot.tree.command(name="setmode")
    async def setmode_command(interaction: discord.Interaction, 
                            mode: str, 
                            duration: int = None):
        await bot.ai_handler.setmode_command(interaction, mode, duration)

    @bot.tree.command(name="listmodes")
    async def listmodes_command(interaction: discord.Interaction):
        await bot.ai_handler.listmodes_command(interaction)