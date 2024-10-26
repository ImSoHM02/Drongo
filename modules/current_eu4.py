# modules/current_eu4.py

import discord
from discord import app_commands

# This dictionary should be stored in a database or a separate configuration file in a real-world scenario
current_games = {
    'Indochina': {'session_id': '1', 'last_session': 4, 'next_session': 5},
    'All my homies love Europe': {'session_id': 'N/A', 'last_session': 0, 'next_session': 0}
}

async def current_eu4(interaction: discord.Interaction):
    if not current_games:
        await interaction.response.send_message("No current EU4 games are listed.", ephemeral=True)
        return

    description_lines = ["**Current EU4 Games:**"]
    for game_name, details in current_games.items():
        description_lines.append(f"**{game_name}** - Session ID: {details['session_id']}, Last Session: {details['last_session']}, Next Session: {details['next_session']}")

    await interaction.response.send_message("\n".join(description_lines))

def setup(bot):
    @bot.tree.command(name="current_eu4")
    @app_commands.describe()
    async def current_eu4_command(interaction: discord.Interaction):
        await current_eu4(interaction)