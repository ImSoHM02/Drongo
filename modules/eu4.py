# modules/eu4.py

import discord
import aiohttp
from discord import app_commands
from modules.stats_display import StatsDisplay

# Moved from current_eu4.py
current_games = {
    'Indochina': {'session_id': '1', 'last_session': 4, 'next_session': 5},
    'All my homies love Europe': {'session_id': 'N/A', 'last_session': 0, 'next_session': 0}
}

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

async def current_eu4(interaction: discord.Interaction):
    if not current_games:
        await interaction.response.send_message("No current EU4 games are listed.", ephemeral=True)
        return

    description_lines = ["**Current EU4 Games:**"]
    for game_name, details in current_games.items():
        description_lines.append(f"**{game_name}** - Session ID: {details['session_id']}, Last Session: {details['last_session']}, Next Session: {details['next_session']}")

    await interaction.response.send_message("\n".join(description_lines))

def setup(bot):
    @bot.tree.command(name="eu4")
    @app_commands.describe(
        session_id="The session ID",
        session_number="The session number or identifier",
        title="A title for your message (optional)"
    )
    async def eu4_command(interaction: discord.Interaction, session_id: str, session_number: str, title: str = None):
        await fetch_eu4_screenshot(interaction, session_id, session_number, title)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(name="current_eu4")
    async def current_eu4_command(interaction: discord.Interaction):
        await current_eu4(interaction)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)