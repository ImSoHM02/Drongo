import logging
import re
from database_pool import (
    get_main_pool,
    get_db_connection as pool_get_connection,
    DEFAULT_LEVELING_DB_PATH,
)
from database_utils import optimized_db, batch_store_message

# Basic URL matcher for stripping links from stored message content
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')


def _strip_urls(text: str) -> str:
    """Remove URLs and trim whitespace for storage in chat_history.db."""
    cleaned = URL_PATTERN.sub('', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

async def db_connect(db_name='database/system.db'):
    """
    Legacy function for backward compatibility.
    Prefer using the connection pool for better performance.
    """
    return await pool_get_connection(db_name)

LEVELING_DB_PATH = DEFAULT_LEVELING_DB_PATH

async def get_leveling_db_connection():
    """Convenience helper for opening a leveling database connection."""
    return await pool_get_connection(LEVELING_DB_PATH)

async def create_table(conn):
    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_message_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                UNIQUE(discord_message_id)
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS last_message (
                channel_id TEXT PRIMARY KEY,
                last_message_id TEXT NOT NULL
            );
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_lookup
            ON messages (guild_id, channel_id, user_id, message_content);
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_wordrank
            ON messages (guild_id, message_content, user_id);
        ''')
        await conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_discord_id
            ON messages (discord_message_id);
        ''')

        await conn.commit()
    except Exception as e:
        logging.error(f"An error occurred while creating tables: {e}")

async def set_last_message_id(conn, channel_id, last_message_id):
    try:
        await conn.execute('''
            INSERT INTO last_message (channel_id, last_message_id)
            VALUES (?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
            last_message_id=excluded.last_message_id;
        ''', (channel_id, last_message_id))
        await conn.commit()
    except Exception as e:
        logging.error(f"Failed to set last message ID: {e}")

async def get_last_message_id(conn, channel_id):
    try:
        async with conn.execute("SELECT last_message_id FROM last_message WHERE channel_id=?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logging.error(f"Failed to get last message ID: {e}")
        return None

async def store_message(conn, message, full_message_content):
    """
    Store message with clean text only, deduped by Discord snowflake.
    Attachments, embeds, and URLs are stored separately by store_message_components().

    Args:
        conn: Database connection to chat_history.db
        message: Discord message object
        full_message_content: CLEAN TEXT ONLY (no URLs, attachments, embeds)

    Returns:
        message_id: ID of inserted message, or None if duplicate
    """
    try:
        # Clean up the message content - remove duplicates within the same message
        words = full_message_content.split()
        half_len = len(words) // 2
        if half_len > 0 and words[:half_len] == words[half_len:]:
            full_message_content = ' '.join(words[:half_len])

        # Strip URLs so only pure text is stored in chat_history.db (may be empty)
        full_message_content = _strip_urls(full_message_content)

        # Skip storage if nothing remains
        if not full_message_content:
            return None

        # Insert with OR IGNORE relying on discord_message_id uniqueness
        cursor = await conn.execute('''
            INSERT OR IGNORE INTO messages (
                discord_message_id,
                user_id,
                guild_id,
                channel_id,
                message_content,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            str(message.id),
            str(message.author.id),
            str(message.guild.id),
            str(message.channel.id),
            full_message_content,
            message.created_at.isoformat()
        ))

        await conn.commit()

        if cursor.rowcount == 0:
            # Duplicate based on discord_message_id; fetch existing id so we can still store components
            async with conn.execute(
                "SELECT id FROM messages WHERE discord_message_id = ?",
                (str(message.id),)
            ) as cursor2:
                row = await cursor2.fetchone()
                return row[0] if row else None

        return cursor.lastrowid  # Return ID for use in store_message_components

    except Exception as e:
        logging.error(f"An error occurred while storing the message: {e}")
        return None

async def store_message_components(message, message_id):
    """Components are no longer stored separately."""
    return

async def store_attachments(guild_id, message_id, user_id, channel_id, timestamp, attachments):
    """Store message attachments in attachments.db"""
    from database_schema import get_attachments_db_path
    import aiosqlite

    db_path = get_attachments_db_path(guild_id)

    async with aiosqlite.connect(db_path) as conn:
        for attachment in attachments:
            await conn.execute('''
                INSERT INTO attachments (message_id, user_id, guild_id, channel_id, url, filename, content_type, size_bytes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id,
                user_id,
                guild_id,
                channel_id,
                attachment.url,
                attachment.filename,
                attachment.content_type,
                attachment.size,
                timestamp
            ))
        await conn.commit()

async def store_embeds(guild_id, message_id, user_id, channel_id, timestamp, embeds):
    """Store message embeds in embeds.db"""
    from database_schema import get_embeds_db_path
    import aiosqlite

    db_path = get_embeds_db_path(guild_id)

    async with aiosqlite.connect(db_path) as conn:
        for embed in embeds:
            # Insert embed
            cursor = await conn.execute('''
                INSERT INTO embeds (message_id, user_id, guild_id, channel_id, embed_type, title, description, url, color, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id,
                user_id,
                guild_id,
                channel_id,
                embed.type,
                embed.title,
                embed.description,
                embed.url,
                embed.color.value if embed.color else None,
                timestamp
            ))
            embed_id = cursor.lastrowid

            # Insert embed fields
            if embed.fields:
                for field in embed.fields:
                    await conn.execute('''
                        INSERT INTO embed_fields (embed_id, name, value, inline)
                        VALUES (?, ?, ?, ?)
                    ''', (embed_id, field.name, field.value, field.inline))

            # Insert embed images
            if embed.image or embed.thumbnail:
                await conn.execute('''
                    INSERT INTO embed_images (embed_id, image_url, thumbnail_url)
                    VALUES (?, ?, ?)
                ''', (
                    embed_id,
                    embed.image.url if embed.image else None,
                    embed.thumbnail.url if embed.thumbnail else None
                ))

        await conn.commit()

async def store_urls(guild_id, message_id, user_id, channel_id, timestamp, content):
    """
    Extract and store URLs from message content in urls.db.
    Excludes Discord CDN URLs (those are in attachments.db).
    """
    from database_schema import get_urls_db_path
    from urllib.parse import urlparse
    import aiosqlite

    # Extract all URLs from content
    url_pattern = r'https?://[^\s]+'
    urls_found = re.findall(url_pattern, content)

    if not urls_found:
        return

    # Filter out Discord CDN URLs
    cdn_pattern = r'https?://cdn\.discordapp\.com/attachments/[^\s]+'
    non_cdn_urls = [url for url in urls_found if not re.match(cdn_pattern, url)]

    if not non_cdn_urls:
        return

    db_path = get_urls_db_path(guild_id)

    async with aiosqlite.connect(db_path) as conn:
        for position, url in enumerate(non_cdn_urls, 1):
            # Extract domain
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
            except:
                domain = "unknown"

            await conn.execute('''
                INSERT INTO urls (message_id, user_id, guild_id, channel_id, url, domain, url_position, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id,
                user_id,
                guild_id,
                channel_id,
                url,
                domain,
                position,
                timestamp
            ))

        await conn.commit()

async def count_links(conn, user_id, guild_id):
    """
    Count non-attachment URLs for a user.
    Now queries urls.db instead of parsing message_content.

    Args:
        conn: Not used (kept for compatibility)
        user_id: Discord user ID
        guild_id: Discord guild ID
    """
    from database_schema import get_urls_db_path
    import aiosqlite

    db_path = get_urls_db_path(guild_id)

    try:
        async with aiosqlite.connect(db_path) as urls_conn:
            async with urls_conn.execute(
                "SELECT COUNT(*) FROM urls WHERE user_id=? AND guild_id=?",
                (user_id, guild_id)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting links: {e}")
        return 0

async def count_attachments(conn, user_id, guild_id):
    """
    Count attachments for a user.
    Now queries attachments.db instead of parsing message_content.

    Args:
        conn: Not used (kept for compatibility)
        user_id: Discord user ID
        guild_id: Discord guild ID
    """
    from database_schema import get_attachments_db_path
    import aiosqlite

    db_path = get_attachments_db_path(guild_id)

    try:
        async with aiosqlite.connect(db_path) as attachments_conn:
            async with attachments_conn.execute(
                "SELECT COUNT(*) FROM attachments WHERE user_id=? AND guild_id=?",
                (user_id, guild_id)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0
    except Exception as e:
        logging.error(f"Error counting attachments: {e}")
        return 0

async def get_db_connection(db_name='database/system.db'):
    """
    Get database connection with improved connection management.
    Uses connection pooling when available.
    """
    return await pool_get_connection(db_name)

async def initialize_database():
    """Initialize database with optimizations."""
    # Initialize connection pools
    pool = await get_main_pool()

    # Create tables
    conn = await get_db_connection()
    try:
        await create_table(conn)
    finally:
        await conn.close()

    # Add indexes and optimizations
    await optimized_db.add_missing_indexes()
    logging.info("Database initialization completed with optimizations")

# New optimized functions
async def store_message_optimized(message, full_message_content):
    """
    Optimized message storage using batching.
    Use this instead of store_message for better performance.
    """
    await batch_store_message(message, full_message_content)

async def flush_message_batches():
    """Flush any pending message batches."""
    await optimized_db.flush_message_batch()

async def cleanup_old_data(days_to_keep: int = 365):
    """Clean up old database records."""
    return await optimized_db.cleanup_old_data(days_to_keep)

async def get_database_health():
    """Get database health information."""
    return await optimized_db.analyze_database_health()
