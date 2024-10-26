import os
import sys
import asyncio
from discord import app_commands
from discord.ext import commands
from discord import Interaction

class Restart(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.authorized_user_id = int(os.getenv("AUTHORIZED_USER_ID"))

    @app_commands.command(name="restart", description="Restart the bot and refresh its code")
    async def restart(self, interaction: Interaction):
        if interaction.user.id != self.authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message("fuck i'm entering the goon cave")
        await self.bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)

async def setup(bot):
    await bot.add_cog(Restart(bot))