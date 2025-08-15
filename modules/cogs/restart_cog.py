import os
import sys
import discord
from discord.ext import commands
from discord import app_commands

class RestartCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="restart", description="Restart the bot and refresh its code")
    async def restart(self, interaction: discord.Interaction):
        authorized_user_id = int(os.getenv("AUTHORIZED_USER_ID"))
        if interaction.user.id != authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message("fuck i'm entering the goon cave")
        await self.bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)

async def setup(bot):
    await bot.add_cog(RestartCog(bot))