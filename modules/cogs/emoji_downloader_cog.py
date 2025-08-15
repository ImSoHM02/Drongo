import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import zipfile
import io
import asyncio
import re

class EmojiDownloaderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def download_and_zip_emojis(self, guild: discord.Guild, interaction: discord.Interaction) -> io.BytesIO:
        """Downloads all emojis from a guild, zips them, and provides progress updates."""
        emoji_data = []
        total_emojis = len(guild.emojis)
        for i, emoji in enumerate(guild.emojis):
            try:
                async with self.session.get(str(emoji.url)) as resp:
                    if resp.status == 200:
                        emoji_data.append(
                            (f"{emoji.name}.{'gif' if emoji.animated else 'png'}", await resp.read())
                        )
                    else:
                        print(f"Failed to download emoji: {emoji.name} with status code: {resp.status}")
            except Exception as e:
                print(f"Error downloading emoji {emoji.name}: {e}")

            if (i + 1) % 5 == 0 or (i + 1) == total_emojis:
                progress = (i + 1) / total_emojis * 100
                try:
                    await interaction.edit_original_response(
                        content=f"stealin' emojis: {progress:.1f}% complete ({i + 1}/{total_emojis})"
                    )
                except discord.errors.NotFound:
                    print("Interaction not found during progress update. It might have expired.")
                    return None
            await asyncio.sleep(0.1)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for filename, data in emoji_data:
                zip_file.writestr(filename, data)
        zip_buffer.seek(0)
        return zip_buffer

    async def download_and_zip_message_emojis(self, messages, interaction: discord.Interaction) -> io.BytesIO:
        """Downloads emojis found in messages, zips them, and provides progress updates."""
        emoji_data = []
        seen_emojis = set()
        custom_emoji_pattern = r'<(?:a)?:([a-zA-Z0-9_]+):(\d+)>'
        total_messages = len(messages)
        await interaction.edit_original_response(content=f"Scanning messages for emojis (0/{total_messages})...")
        found_emojis = []
        for i, message in enumerate(messages, 1):
            if i % 10 == 0 or i == total_messages:
                await interaction.edit_original_response(
                    content=f"Scanning messages for emojis ({i}/{total_messages})..."
                )
            matches = re.finditer(custom_emoji_pattern, message.content)
            for match in matches:
                emoji_name = match.group(1)
                emoji_id = match.group(2)
                is_animated = match.group(0).startswith('<a:')
                if emoji_id not in seen_emojis:
                    seen_emojis.add(emoji_id)
                    found_emojis.append((emoji_name, emoji_id, is_animated))
        if not found_emojis:
            return None
        total_emojis = len(found_emojis)
        for i, (emoji_name, emoji_id, is_animated) in enumerate(found_emojis, 1):
            if i % 2 == 0 or i == total_emojis:
                progress = (i / total_emojis) * 100
                await interaction.edit_original_response(
                    content=f"Downloading emojis: {progress:.1f}% ({i}/{total_emojis})"
                )
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if is_animated else 'png'}"
            try:
                async with self.session.get(emoji_url) as resp:
                    if resp.status == 200:
                        emoji_data.append(
                            (f"{emoji_name}_{emoji_id}.{'gif' if is_animated else 'png'}", await resp.read())
                        )
                    else:
                        print(f"Failed to download emoji: {emoji_name} with status code: {resp.status}")
            except Exception as e:
                print(f"Error downloading emoji {emoji_name}: {e}")
            await asyncio.sleep(0.1)
        if not emoji_data:
            return None
        MAX_ZIP_SIZE = 7 * 1024 * 1024
        current_size = 0
        current_chunk = []
        chunks = []
        for emoji in emoji_data:
            emoji_size = len(emoji[1])
            if current_size + emoji_size > MAX_ZIP_SIZE:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = [emoji]
                current_size = emoji_size
            else:
                current_chunk.append(emoji)
                current_size += emoji_size
        if current_chunk:
            chunks.append(current_chunk)
        zip_buffers = []
        for i, chunk in enumerate(chunks):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename, data in chunk:
                    zip_file.writestr(filename, data)
            zip_buffer.seek(0)
            zip_buffers.append(zip_buffer)
        return zip_buffers

    @app_commands.command(name="download_emojis")
    @app_commands.describe(confirm="Type 'yes' to confirm downloading all server emojis")
    async def download_emojis_command(self, interaction: discord.Interaction, confirm: str):
        """Downloads all emojis from the server and sends them as a zip file."""
        if confirm.lower() != "yes":
            await interaction.response.send_message(
                "Command cancelled. Please type 'yes' to confirm.", ephemeral=True
            )
            return
        await interaction.response.defer(thinking=True)
        try:
            await interaction.edit_original_response(content="Starting emoji stealin'...")
            zip_buffer = await self.download_and_zip_emojis(interaction.guild, interaction)
            if zip_buffer is None:
                await interaction.followup.send("An error occurred during emoji download. Please check the logs.")
                return
            await interaction.edit_original_response(content="Emojis jacked! Sending zip file...")
            await interaction.followup.send(
                "Here are all the emojis from this server:",
                file=discord.File(zip_buffer, filename="server_emojis.zip"),
            )
            self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="save_channel_emojis")
    @app_commands.describe(message_limit="Number of messages to check (default: 100, max: 1000)")
    async def save_channel_emojis(self, interaction: discord.Interaction, message_limit: int = 100):
        """Downloads all custom emojis found in recent channel messages."""
        await interaction.response.defer(thinking=True)
        if message_limit > 1000:
            message_limit = 1000
            await interaction.followup.send("Message limit capped at 1000 messages.")
        try:
            messages = [msg async for msg in interaction.channel.history(limit=message_limit)]
            zip_buffers = await self.download_and_zip_message_emojis(messages, interaction)
            if zip_buffers is None:
                await interaction.followup.send("No custom emojis found in the messages.")
                return
            if len(zip_buffers) == 1:
                await interaction.followup.send(
                    "Here are all the custom emojis found in the messages:",
                    file=discord.File(zip_buffers[0], filename="channel_emojis.zip"),
                )
            else:
                await interaction.followup.send("Sending emojis in multiple parts due to file size:")
                for i, buffer in enumerate(zip_buffers, 1):
                    await interaction.followup.send(
                        f"Emoji pack part {i}/{len(zip_buffers)}:",
                        file=discord.File(buffer, filename=f"channel_emojis_part{i}.zip"),
                    )
            self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(EmojiDownloaderCog(bot))