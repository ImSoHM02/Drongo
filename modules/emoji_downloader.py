import discord
from discord import app_commands
import aiohttp
import zipfile
import io
import asyncio
import re

async def download_and_zip_emojis(guild: discord.Guild, interaction: discord.Interaction) -> io.BytesIO:
    """Downloads all emojis from a guild, zips them, and provides progress updates."""

    emoji_data = []
    total_emojis = len(guild.emojis)
    async with aiohttp.ClientSession() as session:
        for i, emoji in enumerate(guild.emojis):
            try:
                async with session.get(str(emoji.url)) as resp:
                    if resp.status == 200:
                        emoji_data.append(
                            (f"{emoji.name}.{'gif' if emoji.animated else 'png'}", await resp.read())
                        )
                    else:
                        print(f"Failed to download emoji: {emoji.name} with status code: {resp.status}")
            except Exception as e:
                print(f"Error downloading emoji {emoji.name}: {e}")

            # Update progress every 5 emojis or at the end
            if (i + 1) % 5 == 0 or (i + 1) == total_emojis:
                progress = (i + 1) / total_emojis * 100
                try:
                    await interaction.edit_original_response(
                        content=f"stealin' emojis: {progress:.1f}% complete ({i + 1}/{total_emojis})"
                    )
                except discord.errors.NotFound:
                    print("Interaction not found during progress update. It might have expired.")
                    return None  # Stop further processing if interaction is not found

            await asyncio.sleep(0.1)  # Introduce a small delay to help avoid rate limits

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, data in emoji_data:
            zip_file.writestr(filename, data)

    zip_buffer.seek(0)
    return zip_buffer

async def download_and_zip_message_emojis(messages, interaction: discord.Interaction) -> io.BytesIO:
    """Downloads emojis found in messages, zips them, and provides progress updates."""
    emoji_data = []
    seen_emojis = set()  # Track unique emoji IDs
    custom_emoji_pattern = r'<(?:a)?:([a-zA-Z0-9_]+):(\d+)>'
    
    async with aiohttp.ClientSession() as session:
        for message in messages:
            matches = re.finditer(custom_emoji_pattern, message.content)
            for match in matches:
                emoji_name = match.group(1)
                emoji_id = match.group(2)
                is_animated = match.group(0).startswith('<a:')
                
                # Skip if we've already processed this emoji
                if emoji_id in seen_emojis:
                    continue
                seen_emojis.add(emoji_id)
                
                # Create emoji URL
                emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if is_animated else 'png'}"
                
                try:
                    async with session.get(emoji_url) as resp:
                        if resp.status == 200:
                            emoji_data.append(
                                (f"{emoji_name}_{emoji_id}.{'gif' if is_animated else 'png'}", await resp.read())
                            )
                        else:
                            print(f"Failed to download emoji: {emoji_name} with status code: {resp.status}")
                except Exception as e:
                    print(f"Error downloading emoji {emoji_name}: {e}")
                
                await asyncio.sleep(0.1)  # Rate limiting prevention

    if not emoji_data:
        return None

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, data in emoji_data:
            zip_file.writestr(filename, data)

    zip_buffer.seek(0)
    return zip_buffer

def setup(bot):
    @bot.tree.command(name="download_emojis")
    @app_commands.describe(
        confirm="Type 'yes' to confirm downloading all server emojis"
    )
    async def download_emojis_command(interaction: discord.Interaction, confirm: str):
        """Downloads all emojis from the server and sends them as a zip file."""

        if confirm.lower() != "yes":
            await interaction.response.send_message(
                "Command cancelled. Please type 'yes' to confirm.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            await interaction.edit_original_response(content="Starting emoji stealin'...")
            zip_buffer = await download_and_zip_emojis(interaction.guild, interaction)

            # Check if zip_buffer is None, indicating a potential error during download
            if zip_buffer is None:
                await interaction.followup.send("An error occurred during emoji download. Please check the logs.")
                return

            await interaction.edit_original_response(content="Emojis jacked! Sending zip file...")
            await interaction.followup.send(
                "Here are all the emojis from this server:",
                file=discord.File(zip_buffer, filename="server_emojis.zip"),
            )
            bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")

    @bot.tree.command(name="save_channel_emojis")
    @app_commands.describe(
        message_limit="Number of messages to check (default: 100, max: 1000)"
    )
    async def save_channel_emojis(interaction: discord.Interaction, message_limit: int = 100):
        """Downloads all custom emojis found in recent channel messages."""
        await interaction.response.defer(thinking=True)
        
        # Limit the message search to a reasonable number
        if message_limit > 1000:
            message_limit = 1000
            await interaction.followup.send("Message limit capped at 1000 messages.")
        
        try:
            await interaction.followup.send(f"Scanning {message_limit} messages for custom emojis...")
            messages = [msg async for msg in interaction.channel.history(limit=message_limit)]
            
            zip_buffer = await download_and_zip_message_emojis(messages, interaction)
            
            if zip_buffer is None:
                await interaction.followup.send("No custom emojis found in the messages.")
                return
            
            await interaction.followup.send(
                "Here are all the custom emojis found in the messages:",
                file=discord.File(zip_buffer, filename="channel_emojis.zip"),
            )
            bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)
            
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")