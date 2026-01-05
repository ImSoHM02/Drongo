import discord
from discord.ext import commands
from discord import app_commands
import aiohttp

class JellyfinCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_public_ip(self):
        """Get the public IP address."""
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org') as response:
                if response.status == 200:
                    return await response.text()
                return None

    @app_commands.command(name="jellyfin", description="Get the link to the Jellyfin server")
    async def jellyfin(self, interaction: discord.Interaction):
        """Provides a link to the Jellyfin server with the current IP."""
        await interaction.response.defer()
        ip_address = await self.get_public_ip()
        if ip_address:
            message = (f"Oi cunts, the Jellyfin server is at: http://{ip_address}:8096\n"
                       f"If you wanna request some media, use Jellyseerr cunt: http://{ip_address}:5055\n"
                       f"Your Jellyseerr login is the same as your Jellyfin login\n")
            await interaction.followup.send(message)
        else:
            await interaction.followup.send("Sorry mate, couldn't get the IP address. Something's cooked.")
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

async def setup(bot):
    await bot.add_cog(JellyfinCog(bot))
