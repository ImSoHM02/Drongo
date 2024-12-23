# modules/web_link.py

import socket
import discord
from discord import app_commands

def get_ip():
    """Get the primary non-localhost IPv4 address"""
    import subprocess
    import platform
    
    try:
        if platform.system() == "Linux":
            # Use hostname -I to get all IPs and take the first one
            output = subprocess.check_output("hostname -I", shell=True).decode().strip()
            ips = output.split()
            return ips[0] if ips else '127.0.0.1'
        else:
            # Fallback for other systems
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('10.255.255.255', 1))
                return s.getsockname()[0]
            finally:
                s.close()
    except Exception as e:
        print(f"Error getting IP: {e}")
        return '127.0.0.1'

def setup(bot):
    @bot.tree.command(name="webstats")
    async def webstats(interaction: discord.Interaction):
        """Get the link to the web statistics interface"""
        await interaction.response.defer()
        ip = get_ip()
        await interaction.followup.send(
            f"Web Statistics Interface: http://{ip}:5000"
        )
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)
