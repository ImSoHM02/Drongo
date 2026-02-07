import os
import logging
from dotenv import load_dotenv

load_dotenv('id.env')

token = os.getenv("DISCORD_BOT_TOKEN")
if not token:
    raise ValueError("DISCORD_BOT_TOKEN is not set in the environment variables")

client_id = os.getenv("DISCORD_CLIENT_ID")
if not client_id:
    raise ValueError("DISCORD_CLIENT_ID is not set in the environment variables")

authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
my_user_id = os.getenv("BLACKTHENWHITE_USER_ID")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")

logging.info("Environment variables validated successfully")
