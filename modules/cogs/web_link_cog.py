import socket
import discord
from discord.ext import commands
from discord import app_commands
import subprocess
import platform
import logging

class WebLinkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_ip(self):
        """Get the primary non-localhost IPv4 address"""
        try:
            if platform.system() == "Linux":
                output = subprocess.check_output("hostname -I", shell=True).decode().strip()
                ips = output.split()
                return ips[0] if ips else '127.0.0.1'
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    s.connect(('10.255.255.255', 1))
                    return s.getsockname()[0]
                finally:
                    s.close()
        except Exception as e:
            logging.error(f"Error getting IP address: {e}")
            return '127.0.0.1'

    @app_commands.command(name="webstats")
    async def webstats(self, interaction: discord.Interaction):
        """Get the link to the web statistics interface"""
        await interaction.response.defer()
        ip = self.get_ip()
        await interaction.followup.send(
            f"Web Statistics Interface: http://{ip}:5000"
        )
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

async def setup(bot):
    await bot.add_cog(WebLinkCog(bot))