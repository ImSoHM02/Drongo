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
            "name": "eu4",
            "description": "Fetches an EU4 session screenshot.",
            "options": [
                {
                    "name": "session_id",
                    "description": "The session ID",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "session_number",
                    "description": "The session number or identifier",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "title",
                    "description": "A title for your message (optional)",
                    "type": 3,
                    "required": False
                }
            ]
        },
        {
            "name": "current_eu4",
            "description": "Current games with their session id, previous session number and next session number."
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
            "name": "track_game",
            "description": "Track a game for price alerts",
            "options": [
                {
                    "name": "game_name",
                    "description": "The name of the game to track",
                    "type": 3,  # Type 3 is for STRING
                    "required": True
                }
            ]
        },
        {
            "name": "untrack_game",
            "description": "Stop tracking a game",
            "options": [
                {
                    "name": "game_name",
                    "description": "The name of the game to stop tracking",
                    "type": 3,  # Type 3 is for STRING
                    "required": True
                }
            ]
        },
        {
            "name": "list_tracked_games",
            "description": "List all games you're currently tracking"
        },
        {
            "name": "clearchat",
            "description": "Clear your chat history with the bot"
        },
        {
            "name": "minecraft_info",
            "description": "Get the current IP and statistics for the Minecraft server"
        },
        {
            "name": "minecraft_start",
            "description": "Start the Minecraft server"
        },
        {
            "name": "minecraft_restart",
            "description": "Restart the Minecraft server"
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
        },
        {
            "name": "generate_statblock",
            "description": "Generate a D&D-style stat block image",
            "options": [
                {
                    "name": "name",
                    "description": "The name of the creature",
                    "type": 3,  # STRING
                    "required": True
                },
                {
                    "name": "size",
                    "description": "Size (Tiny/Small/Medium/Large/Huge/Gargantuan)",
                    "type": 3,  # STRING
                    "required": True,
                    "choices": [
                        {"name": "Tiny", "value": "tiny"},
                        {"name": "Small", "value": "small"},
                        {"name": "Medium", "value": "medium"},
                        {"name": "Large", "value": "large"},
                        {"name": "Huge", "value": "huge"},
                        {"name": "Gargantuan", "value": "gargantuan"}
                    ]
                },
                {
                    "name": "type",
                    "description": "Type of creature (e.g., humanoid, beast)",
                    "type": 3,  # STRING
                    "required": True
                },
                {
                    "name": "alignment",
                    "description": "Creature's alignment",
                    "type": 3,  # STRING
                    "required": True
                },
                {
                    "name": "ac",
                    "description": "Armor Class value",
                    "type": 4,  # INTEGER
                    "required": True
                },
                {
                    "name": "hp",
                    "description": "Hit Points value",
                    "type": 4,  # INTEGER
                    "required": True
                },
                {
                    "name": "speed",
                    "description": "Movement speed",
                    "type": 3,  # STRING
                    "required": True
                },
                {
                    "name": "strength",
                    "description": "Strength score (1-30)",
                    "type": 4,  # INTEGER
                    "required": True,
                    "min_value": 1,
                    "max_value": 30
                },
                {
                    "name": "dexterity",
                    "description": "Dexterity score (1-30)",
                    "type": 4,  # INTEGER
                    "required": True,
                    "min_value": 1,
                    "max_value": 30
                },
                {
                    "name": "constitution",
                    "description": "Constitution score (1-30)",
                    "type": 4,  # INTEGER
                    "required": True,
                    "min_value": 1,
                    "max_value": 30
                },
                {
                    "name": "intelligence",
                    "description": "Intelligence score (1-30)",
                    "type": 4,  # INTEGER
                    "required": True,
                    "min_value": 1,
                    "max_value": 30
                },
                {
                    "name": "wisdom",
                    "description": "Wisdom score (1-30)",
                    "type": 4,  # INTEGER
                    "required": True,
                    "min_value": 1,
                    "max_value": 30
                },
                {
                    "name": "charisma",
                    "description": "Charisma score (1-30)",
                    "type": 4,  # INTEGER
                    "required": True,
                    "min_value": 1,
                    "max_value": 30
                },
                {
                    "name": "challenge",
                    "description": "Challenge rating (e.g., '1/4', '2', '10')",
                    "type": 3,  # STRING
                    "required": True
                },
                {
                    "name": "resistances",
                    "description": "Damage resistances",
                    "type": 3,  # STRING
                    "required": False
                },
                {
                    "name": "senses",
                    "description": "Senses",
                    "type": 3,  # STRING
                    "required": False
                },
                {
                    "name": "languages",
                    "description": "Languages",
                    "type": 3,  # STRING
                    "required": False
                },
                {
                    "name": "feature_name",
                    "description": "Name of special feature",
                    "type": 3,  # STRING
                    "required": False
                },
                {
                    "name": "feature_desc",
                    "description": "Description of special feature",
                    "type": 3,  # STRING
                    "required": False
                },
                {
                    "name": "action_name",
                    "description": "Name of action",
                    "type": 3,  # STRING
                    "required": False
                },
                {
                    "name": "action_desc",
                    "description": "Description of action",
                    "type": 3,  # STRING
                    "required": False
                }
            ]
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
