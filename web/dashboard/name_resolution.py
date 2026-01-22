import logging
import time
from typing import Dict, List, Optional

import discord

from . import state


def validate_guild_id(guild_id) -> Optional[int]:
    """Validate guild_id for dashboard operations."""
    if guild_id is None:
        return None

    if isinstance(guild_id, int):
        return guild_id

    if isinstance(guild_id, str):
        if guild_id.startswith("test_guild_"):
            logging.warning(f"Test guild ID detected in dashboard: {guild_id}. Rejecting request.")
            return None

        try:
            return int(guild_id)
        except ValueError:
            logging.error(f"Invalid guild_id in dashboard request: '{guild_id}'")
            return None

    return None


async def resolve_user_name(user_id: str) -> str:
    """Resolve user ID to display name with caching."""
    cache_key = f"user_{user_id}"
    current_time = time.time()

    if cache_key in state.name_cache and cache_key in state.cache_expiry:
        if current_time < state.cache_expiry[cache_key]:
            return state.name_cache[cache_key]

    if not state.bot_instance:
        logging.debug("Bot instance not available for user name resolution")
        return f"User ({user_id})"

    try:
        try:
            validated_user_id = int(user_id)
        except ValueError:
            logging.warning(f"Invalid user_id in dashboard request: '{user_id}'")
            return "Invalid User ID"

        user = state.bot_instance.get_user(validated_user_id)
        if not user:
            try:
                user = await state.bot_instance.fetch_user(validated_user_id)
            except discord.NotFound:
                logging.debug(f"User {user_id} not found on Discord")
            except discord.HTTPException as e:
                logging.debug(f"HTTP error fetching user {user_id}: {e}")

        if user:
            display_name = user.display_name
            state.name_cache[cache_key] = display_name
            state.cache_expiry[cache_key] = current_time + state.CACHE_DURATION
            logging.debug(f"Resolved user {user_id} to {display_name} via Discord API")
            return display_name

        logging.debug(f"User {user_id} not found in Discord")
    except Exception as e:
        logging.error(f"Error resolving user name via Discord API: {e}")

    fallback_name = f"User ({user_id})"
    state.name_cache[cache_key] = fallback_name
    state.cache_expiry[cache_key] = current_time + 30
    logging.debug(f"Using fallback name for user {user_id}: {fallback_name}")
    return fallback_name


async def resolve_guild_name(guild_id: str) -> str:
    """Resolve guild ID to guild name with caching."""
    cache_key = f"guild_{guild_id}"
    current_time = time.time()

    if cache_key in state.name_cache and cache_key in state.cache_expiry:
        if current_time < state.cache_expiry[cache_key]:
            return state.name_cache[cache_key]

    if not state.bot_instance:
        logging.debug("Bot instance not available for guild name resolution")
        return f"Guild ({guild_id})"

    try:
        validated_guild_id = validate_guild_id(guild_id)
        if validated_guild_id is None:
            return "Invalid Guild ID"

        guild = state.bot_instance.get_guild(validated_guild_id)
        if not guild:
            try:
                guild = await state.bot_instance.fetch_guild(validated_guild_id)
            except discord.NotFound:
                logging.debug(f"Guild {guild_id} not found on Discord")
            except discord.HTTPException as e:
                logging.debug(f"HTTP error fetching guild {guild_id}: {e}")

        if guild:
            display_name = guild.name
            state.name_cache[cache_key] = display_name
            state.cache_expiry[cache_key] = current_time + state.CACHE_DURATION
            logging.debug(f"Resolved guild {guild_id} to {display_name} via Discord API")
            return display_name

        logging.debug(f"Guild {guild_id} not found in Discord")
    except Exception as e:
        logging.error(f"Error resolving guild name via Discord API: {e}")

    fallback_name = f"Guild ({guild_id})"
    state.name_cache[cache_key] = fallback_name
    state.cache_expiry[cache_key] = current_time + 30
    logging.debug(f"Using fallback name for guild {guild_id}: {fallback_name}")
    return fallback_name


async def bulk_resolve_names(user_ids: Optional[List[str]] = None, guild_ids: Optional[List[str]] = None) -> Dict[str, str]:
    """Bulk resolve multiple user and guild names."""
    resolved_names: Dict[str, str] = {}

    if user_ids:
        for user_id in user_ids:
            resolved_names[f"user_{user_id}"] = await resolve_user_name(user_id)

    if guild_ids:
        for guild_id in guild_ids:
            resolved_names[f"guild_{guild_id}"] = await resolve_guild_name(guild_id)

    return resolved_names
