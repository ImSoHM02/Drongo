import aiohttp
import asyncio
import os
import sys
from dotenv import load_dotenv

# Load the environment variables from id.env in parent directory
load_dotenv('../id.env')

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
            "name": "save_channel_emojis",
            "description": "Save all custom emojis found in recent channel messages.",
            "options": [
                {
                    "name": "message_limit",
                    "description": "Number of messages to check (default: 100, max: 1000)",
                    "type": 4,  # Type 4 is for INTEGER
                    "required": False
                }
            ]
        },
        {
            "name": "ai_setmode",
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
                        {"name": "Not-Friendly", "value": "not-friendly"},
                        {"name": "Test Insults", "value": "test-insults"},
                        {"name": "Test Compliments", "value": "test-compliments"}
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
            "name": "ai_listmodes",
            "description": "List all available response modes"
        },
        {
            "name": "webstats",
            "description": "Get the link to the web statistics interface"
        },
        {
            "name": "achievements",
            "description": "Check your achievement progress"
        },
        {
            "name": "clear_achievements",
            "description": "Clear achievements for a specified user (Admin only)",
            "options": [
                {
                    "name": "user",
                    "description": "The user whose achievements should be cleared",
                    "type": 6,  # Type 6 is for USER
                    "required": True
                }
            ]
        },
        {
            "name": "achievement_leaderboard",
            "description": "View the achievement leaderboard"
        },
        {
            "name": "sra",
            "description": "Get a random Steam achievement",
            "options": [
                {
                    "name": "game",
                    "description": "The name or App ID of the Steam game",
                    "type": 3,  # Type 3 is for STRING
                    "required": True
                }
            ]
        }
    ]

async def register_commands():
    print("====== REGISTER COMMANDS ======")

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
