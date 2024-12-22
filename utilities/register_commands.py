import aiohttp
import asyncio
import os
from dotenv import load_dotenv

# Load the environment variables from id.env
load_dotenv('id.env')

def get_commands():
    return [
        {
            "name": "wordcount",
            "description": "Counts how many times a user has said a word or phrase within this server.",
            "options": [
                {
                    "name": "user",
                    "description": "The user to check",
                    "type": 6,  # Type 6 is for USER
                    "required": True 
                },
                {
                    "name": "word",
                    "description": "The word or phrase to count",
                    "type": 3,  # Type 3 is for STRING
                    "required": True 
                }
            ]
        },
        {
            "name": "stats",
            "description": "Message statistics commands",
            "options": [
                {
                    "name": "attachments",
                    "description": "Count attachments for a user",
                    "type": 1,  # SUB_COMMAND
                    "options": [
                        {
                            "name": "user",
                            "description": "The user whose attachment count to retrieve",
                            "type": 6,  # USER
                            "required": True
                        }
                    ]
                },
                {
                    "name": "links",
                    "description": "Count links for a user",
                    "type": 1,  # SUB_COMMAND
                    "options": [
                        {
                            "name": "user",
                            "description": "The user whose link count to retrieve",
                            "type": 6,  # USER
                            "required": True
                        }
                    ]
                }
            ]
        },
        {
            "name": "delete_messages",
            "description": "Deletes the specified number of bot messages.",
            "options": [
                {
                    "name": "count",
                    "description": "The number of bot messages to delete",
                    "type": 4,  # Type 4 is for INTEGER
                    "required": True
                }
            ]
        },
        {
            "name": "clearchat",
            "description": "Clear your chat history with the bot"
        },
        {
            "name": "restart",
            "description": "Restart the bot and refresh its code"
        },
        {
            "name": "wordrank",
            "description": "Ranks users by how many times they've used a specific word or phrase.",
            "options": [
                {
                    "name": "word",
                    "description": "The word or phrase to rank users by",
                    "type": 3,  # Type 3 is for STRING
                    "required": True 
                }
            ]
        },
        {
            "name": "download_emojis",
            "description": "Download all server emojis, zip them, and post as an attachment.",
            "options": [
                {
                    "name": "confirm",
                    "description": "Type 'yes' to confirm downloading all server emojis",
                    "type": 3,  # Type 3 is for STRING
                    "required": True
                }
            ]
        },
        {
            "name": "setmode",
            "description": "Set the bot's response mode with optional duration",
            "options": [
                {
                    "name": "mode",
                    "description": "The mode to set",
                    "type": 3,  # STRING
                    "required": True,
                    "choices": [
                        {"name": "Default", "value": "default"},
                        {"name": "Friendly", "value": "friendly"},
                        {"name": "Not-Friendly", "value": "not-friendly"}
                    ]
                },
                {
                    "name": "duration",
                    "description": "Duration in seconds before reverting to default mode",
                    "type": 4,  # INTEGER
                    "required": False
                }
            ]
        },
        {
            "name": "listmodes",
            "description": "List all available response modes"
        }
    ]

async def register_commands():
    print("====== REGISTER COMMANDS ======")

    token = os.getenv("DISCORD_BOT_TOKEN")
    client_id = os.getenv("DISCORD_CLIENT_ID")
    guild_ids = os.getenv("DISCORD_GUILD_ID").split(',')

    commands = get_commands()
    
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bot {token}"}
        
        for guild_id in guild_ids:
            guild_id = guild_id.strip()  # Remove any whitespace
            url = f"https://discord.com/api/v9/applications/{client_id}/guilds/{guild_id}/commands"
            
            print(f"Registering commands for guild {guild_id}...")
            async with session.put(url, json=commands, headers=headers) as response:
                if response.status == 200:
                    print(f"Successfully registered commands for guild {guild_id}")
                else:
                    print(f"Failed to register commands for guild {guild_id}", await response.text())

if __name__ == "__main__":
    asyncio.run(register_commands())
