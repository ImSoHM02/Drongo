import discord
from discord.ext import commands
from discord import app_commands

class ClearChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="clearchat")
    async def clear_chat(self, interaction: discord.Interaction):
        """Clear your chat history with the bot."""
        self.bot.ai_handler.conversation_manager.clear_history(str(interaction.user.id))
        await interaction.response.send_message("Your chat history has been cleared, dickhead", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ClearChatCog(bot))