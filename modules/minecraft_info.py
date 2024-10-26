import discord
from discord import app_commands
import asyncio
import mcstatus
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('id.env')
AUTHORIZED_USER_ID = os.getenv("AUTHORIZED_USER_ID")

async def get_public_ip():
    try:
        proc = await asyncio.create_subprocess_exec(
            'curl', 'ifconfig.me',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode('utf-8').strip()
        else:
            return "Unable to retrieve public IP"
    except Exception:
        return "Unable to retrieve public IP"

async def get_minecraft_stats():
    server_dir = "/home/sean/minecraft"
    
    try:
        with open(f"{server_dir}/server.properties", 'r') as f:
            properties = dict(line.strip().split('=') for line in f if '=' in line)
        
        server = await mcstatus.JavaServer.async_lookup(f"localhost:{properties.get('server-port', '25565')}")
        status = await server.async_status()
        
        return {
            "port": properties.get("server-port", "25565"),
            "max_players": properties.get("max-players", "Unknown"),
            "online_players": status.players.online
        }
    except FileNotFoundError:
        return {"error": "Minecraft server files not found"}
    except Exception as e:
        return {"error": f"Error retrieving Minecraft server data: {str(e)}"}

async def minecraft_info(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    ip = await get_public_ip()
    mc_stats = await get_minecraft_stats()
    
    embed = discord.Embed(title="Minecraft Server Info", color=discord.Color.green())
    embed.add_field(name="Server IP", value=f"`{ip}`", inline=False)
    
    if "error" in mc_stats:
        embed.add_field(name="Error", value=mc_stats['error'], inline=False)
        embed.color = discord.Color.red()
    else:
        embed.add_field(name="Server Port", value=mc_stats['port'], inline=True)
        embed.add_field(name="Max Players", value=mc_stats['max_players'], inline=True)
        embed.add_field(name="Online Players", value=mc_stats['online_players'], inline=True)
    
    await interaction.followup.send(embed=embed)

async def start_minecraft_server(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    server_dir = "/home/sean/minecraft"
    start_script = f"{server_dir}/startserver.sh"
    
    if not os.path.exists(start_script):
        await interaction.followup.send("Error: Minecraft start script not found.")
        return

    try:
        # Check if a screen session for the server already exists
        check_screen = await asyncio.create_subprocess_exec(
            'screen', '-list',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await check_screen.communicate()
        if "minecraft_server" in stdout.decode():
            await interaction.followup.send("Minecraft server is already running in a screen session.")
            return

        # Ensure the start script is executable
        os.chmod(start_script, 0o755)

        # Start the server in a new screen session with logging
        log_file = f"{server_dir}/minecraft_server.log"
        start_cmd = f"cd {server_dir} && ./startserver.sh >> {log_file} 2>&1"
        process = await asyncio.create_subprocess_shell(
            f"screen -dmS minecraft_server bash -c '{start_cmd}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait a bit and check if the screen session was created successfully
        await asyncio.sleep(5)
        check_screen = await asyncio.create_subprocess_exec(
            'screen', '-list',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await check_screen.communicate()
        
        if "minecraft_server" in stdout.decode():
            await interaction.followup.send("Minecraft server is starting, please allow a few moments for it to fully initialize.")
        else:
            # If screen session wasn't created, check the log file for errors
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_content = f.read()
                await interaction.followup.send(f"Failed to start Minecraft server. Here are the last few lines of the log:\n```\n{log_content[-1000:]}```")
            else:
                await interaction.followup.send("Failed to start Minecraft server and no log file was created. Please check the server manually.")
    except Exception as e:
        await interaction.followup.send(f"Error starting Minecraft server: {str(e)}")

async def restart_minecraft_server(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    server_dir = "/home/sean/minecraft"
    
    try:
        # Check if the screen session exists
        check_screen = await asyncio.create_subprocess_exec(
            'screen', '-list',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await check_screen.communicate()
        if "minecraft_server" not in stdout.decode():
            await interaction.followup.send("Minecraft server is not currently running. No need to restart.")
            return

        # Send stop command to the server
        stop_cmd = "screen -S minecraft_server -X stuff 'stop\n'"
        await asyncio.create_subprocess_shell(stop_cmd)
        
        await interaction.followup.send("Minecraft server is shutting down. It will automatically restart in 10 seconds.")

        # We don't need to start the server again, as startserver.sh will handle that
        # Just wait for a bit to allow the restart to begin
        await asyncio.sleep(15)

        # Check if the server has restarted
        check_screen = await asyncio.create_subprocess_exec(
            'screen', '-list',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await check_screen.communicate()
        if "minecraft_server" in stdout.decode():
            await interaction.followup.send("Minecraft server has successfully restarted.")
        else:
            await interaction.followup.send("The Minecraft server may have encountered an issue while restarting. Please check the server logs.")

    except Exception as e:
        await interaction.followup.send(f"Error during Minecraft server restart process: {str(e)}")
        

def is_authorized(interaction: discord.Interaction) -> bool:
    return str(interaction.user.id) == AUTHORIZED_USER_ID

def setup(bot):
    @bot.tree.command(name="minecraft_info")
    async def minecraft_info_command(interaction: discord.Interaction):
        await minecraft_info(interaction)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(name="minecraft_start")
    async def minecraft_start_command(interaction: discord.Interaction):
        if not is_authorized(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        await start_minecraft_server(interaction)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(name="minecraft_restart")
    async def minecraft_restart_command(interaction: discord.Interaction):
        if not is_authorized(interaction):
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
        await restart_minecraft_server(interaction)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)