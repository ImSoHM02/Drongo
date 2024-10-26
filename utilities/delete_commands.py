import aiohttp
import asyncio
import os
from dotenv import load_dotenv

# Load the environment variables from id.env
load_dotenv('id.env')

async def delete_all_commands():
    print("====== DELETE COMMANDS ======")

    token = os.getenv("DISCORD_BOT_TOKEN")
    client_id = os.getenv("DISCORD_CLIENT_ID")
    guild_id = os.getenv("DISCORD_GUILD_ID")

    # Endpoints for both guild-specific and global commands
    guild_commands_url = f"https://discord.com/api/v9/applications/{client_id}/guilds/{guild_id}/commands"
    global_commands_url = f"https://discord.com/api/v9/applications/{client_id}/commands"

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bot {token}"}

        # Delete guild-specific commands
        async with session.put(guild_commands_url, json=[], headers=headers) as response:
            if response.status == 200:
                print("Deleted Guild Commands")
            else:
                print(f"Failed to delete guild-specific commands: {await response.text()}")

        # Delete global commands
        async with session.put(global_commands_url, json=[], headers=headers) as response:
            if response.status == 200:
                print("Deleted Global Commands")
            else:
                print(f"Failed to delete global commands: {await response.text()}")

asyncio.run(delete_all_commands())
