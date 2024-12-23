import socket
import discord
from discord import app_commands

def get_ip():
    # Get the non-localhost IPv4 address
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't need to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

@app_commands.command(
    name="webstats",
    description="Get the link to the web statistics interface"
)
async def webstats(interaction: discord.Interaction):
    ip = get_ip()
    await interaction.response.send_message(
        f"Web Statistics Interface: http://{ip}:5000\n"
        f"Admin Interface: http://{ip}:5000/admin",
        ephemeral=True
    )

async def setup(bot):
    bot.tree.add_command(webstats)
