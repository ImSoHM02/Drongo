# modules/clearchat.py

import discord
from discord import app_commands

def setup(bot):
    @bot.tree.command(name="clearchat")
    async def clear_chat(interaction: discord.Interaction):
        """Clear your chat history with the bot."""
        bot.ai_handler.clear_user_chat_history(str(interaction.user.id))
        await interaction.response.send_message("Your chat history has been cleared, dickhead", ephemeral=True)