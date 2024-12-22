# modules/eu4_screenshot.py

import discord
from discord import app_commands
import aiohttp

async def fetch_eu4_screenshot(interaction: discord.Interaction, session_id: str, session_number: str, title: str = None):
    image_url = f"https://snorl.ax/EU4/{session_id}/{session_number}.png"
    
    # Check if the image exists
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            if response.status != 200:
                await interaction.response.send_message(f"No screenshot found for session ID {session_id}, session number {session_number}.", ephemeral=True)
                return
    
    # Construct the message with an optional title
    if title:
        message_content = f"**{title}**\n{image_url}"
    else:
        message_content = image_url

    await interaction.response.send_message(message_content)

def setup(bot):
    @bot.tree.command(name="eu4")
    @app_commands.describe(
        session_id="The session ID",
        session_number="The session number or identifier",
        title="A title for your message (optional)"
    )
    async def eu4_command(interaction: discord.Interaction, session_id: str, session_number: str, title: str = None):
        await fetch_eu4_screenshot(interaction, session_id, session_number, title)