import os
import sys
from discord import app_commands
from discord import Interaction

def setup(bot):
    @bot.tree.command(name="restart", description="Restart the bot and refresh its code")
    async def restart(interaction: Interaction):
        authorized_user_id = int(os.getenv("AUTHORIZED_USER_ID"))
        if interaction.user.id != authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message("fuck i'm entering the goon cave")
        await bot.close()
        os.execv(sys.executable, ['python'] + sys.argv)
