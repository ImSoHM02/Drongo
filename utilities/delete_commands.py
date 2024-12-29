import aiohttp
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load the environment variables from id.env in parent directory
load_dotenv('../id.env')

async def delete_all_commands():
    print("====== DELETE COMMANDS ======")

    # Check for required environment variables
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Error: DISCORD_BOT_TOKEN environment variable is not set")
        sys.exit(1)

    client_id = os.getenv("DISCORD_CLIENT_ID")
    if not client_id:
        print("Error: DISCORD_CLIENT_ID environment variable is not set")
        sys.exit(1)

    guild_ids = os.getenv("DISCORD_GUILD_ID")
    if not guild_ids:
        print("Error: DISCORD_GUILD_ID environment variable is not set")
        print("Please set DISCORD_GUILD_ID with comma-separated guild IDs")
        sys.exit(1)
    
    guild_ids = guild_ids.split(',')

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bot {token}"}

        # Delete guild-specific commands for each guild
        for guild_id in guild_ids:
            guild_id = guild_id.strip()  # Remove any whitespace
            guild_commands_url = f"https://discord.com/api/v9/applications/{client_id}/guilds/{guild_id}/commands"
            
            print(f"Deleting commands for guild {guild_id}...")
            async with session.put(guild_commands_url, json=[], headers=headers) as response:
                if response.status == 200:
                    print(f"Successfully deleted commands for guild {guild_id}")
                else:
                    print(f"Failed to delete commands for guild {guild_id}", await response.text())

        # Delete global commands
        global_commands_url = f"https://discord.com/api/v9/applications/{client_id}/commands"
        async with session.put(global_commands_url, json=[], headers=headers) as response:
            if response.status == 200:
                print("Deleted Global Commands")
            else:
                print(f"Failed to delete global commands: {await response.text()}")

if __name__ == "__main__":
    asyncio.run(delete_all_commands())
