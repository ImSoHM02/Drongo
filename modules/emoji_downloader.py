import discord
from discord import app_commands
import aiohttp
import zipfile
import io
import asyncio

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
                        content=f"Downloading emojis: {progress:.1f}% complete ({i + 1}/{total_emojis})"
                    )
                except discord.errors.NotFound:
                    print("Interaction not found during progress update. It might have expired.")
                    return None  # Stop further processing if interaction is not found

            await asyncio.sleep(0.1) # Introduce a small delay to help avoid rate limits and allow for updates

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, data in emoji_data:
            zip_file.writestr(filename, data)

    zip_buffer.seek(0)
    return zip_buffer

def setup(bot):
    @bot.tree.command(name="download_emojis")
    @app_commands.checks.has_permissions(manage_emojis=True)
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
            await interaction.edit_original_response(content="Starting emoji download...")
            zip_buffer = await download_and_zip_emojis(interaction.guild, interaction)

            # Check if zip_buffer is None, indicating a potential error during download
            if zip_buffer is None:
                await interaction.followup.send("An error occurred during emoji download. Please check the logs.")
                return

            await interaction.edit_original_response(content="Emojis downloaded! Sending zip file...")
            await interaction.followup.send(
                "Here are all the emojis from this server:",
                file=discord.File(zip_buffer, filename="server_emojis.zip"),
            )
            bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")