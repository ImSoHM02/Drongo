async def get_message_components(guild_id: str, message_id: int) -> dict:
    """
    Attachments/embeds/URLs are no longer tracked separately; return empty components.
    """
    return {"attachments": [], "embeds": [], "urls": []}
