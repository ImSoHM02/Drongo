import aiosqlite
import logging
import re

async def db_connect(db_name='database/chat_history.db'):
    return await aiosqlite.connect(db_name)

async def create_table(conn):
    try:
        # Create voice chat tracking table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS voice_chat_stats (
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                join_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                leave_timestamp TIMESTAMP,
                duration INTEGER DEFAULT 0,
                total_time INTEGER DEFAULT 0,
                join_count INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, channel_id)
            );
        ''')
        
        # Create voice chat session tracking table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS voice_chat_sessions (
                user_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                join_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id)
            );
        ''')

        # Create command stats table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS command_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                command_name TEXT NOT NULL,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, command_name)
            );
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                message_content TEXT NOT NULL,
                timestamp TEXT NOT NULL
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
        
        # Create table for embed fields
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS embed_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                inline BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY (message_id) REFERENCES messages (id)
            );
        ''')
        await conn.commit()
    except Exception as e:
        logging.error(f"An error occurred while creating tables: {e}")

async def create_game_tracker_tables(conn):
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS game_trackers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            game_name TEXT NOT NULL,
            app_id INTEGER NOT NULL,
            current_price REAL,
            last_checked TIMESTAMP,
            last_notified TIMESTAMP,
            plain TEXT NOT NULL
        );
    ''')
    
    # Check if columns exist, if not, add them
    columns_to_check = ['user_id', 'game_name', 'app_id', 'current_price', 'last_checked', 'last_notified', 'plain']
    
    async with conn.execute("PRAGMA table_info(game_trackers)") as cursor:
        existing_columns = await cursor.fetchall()
        existing_column_names = [column[1] for column in existing_columns]

    for column in columns_to_check:
        if column not in existing_column_names:
            column_type = 'REAL' if column == 'current_price' else 'INTEGER' if column == 'app_id' else 'TEXT'
            await conn.execute(f'ALTER TABLE game_trackers ADD COLUMN {column} {column_type};')
    
    await conn.commit()

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
    try:
        # Clean up the message content - remove duplicates within the same message
        words = full_message_content.split()
        half_len = len(words) // 2
        if half_len > 0 and words[:half_len] == words[half_len:]:
            full_message_content = ' '.join(words[:half_len])

        # Check for recent duplicate messages from the same user
        async with conn.execute("""
            SELECT id FROM messages
            WHERE guild_id=? AND channel_id=? AND user_id=? AND message_content=?
            AND timestamp >= datetime(?, '-10 seconds')
        """, (str(message.guild.id), str(message.channel.id), str(message.author.id),
              full_message_content, message.created_at.isoformat())) as cursor:
            if await cursor.fetchone() is None:
                # Insert the message if it's not a duplicate
                cursor = await conn.execute('''
                    INSERT INTO messages (user_id, guild_id, channel_id, message_content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (str(message.author.id), str(message.guild.id), str(message.channel.id),
                      full_message_content, message.created_at.isoformat()))
                message_id = cursor.lastrowid
                
                # Store embed fields if present
                if message.embeds:
                    for embed in message.embeds:
                        if embed.fields:
                            for field in embed.fields:
                                await conn.execute('''
                                    INSERT INTO embed_fields (message_id, name, value, inline)
                                    VALUES (?, ?, ?, ?)
                                ''', (message_id, field.name, field.value, field.inline))
                
                await conn.commit()
    except Exception as e:
        logging.error(f"An error occurred while storing the message: {e}")

async def count_links(conn, user_id, guild_id):
    async with conn.execute("""
        SELECT message_content FROM messages WHERE user_id=? AND guild_id=?
    """, (user_id, guild_id)) as cursor:
        messages = await cursor.fetchall()
        link_count = sum(len(re.findall(r"https?://[^\s]+", msg[0])) - len(re.findall(r"https?://cdn\.discordapp\.com/attachments/[^\s]+", msg[0])) for msg in messages)
        return link_count

async def count_attachments(conn, user_id, guild_id):
    async with conn.execute("""
        SELECT message_content FROM messages WHERE user_id=? AND guild_id=?
    """, (user_id, guild_id)) as cursor:
        messages = await cursor.fetchall()
        attachment_count = sum(len(re.findall(r"https?://cdn\.discordapp\.com/attachments/[^\s]+", msg[0])) for msg in messages)
        return attachment_count

async def add_game_tracker(conn, user_id, game_name, app_id, current_price):
    await conn.execute('''
        INSERT INTO game_trackers (user_id, game_name, app_id, current_price, last_checked, plain)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
    ''', (user_id, game_name, app_id, current_price, game_name.lower()))
    await conn.commit()

async def remove_game_tracker(conn, user_id, game_name):
    await conn.execute('''
        DELETE FROM game_trackers
        WHERE user_id = ? AND game_name = ?
    ''', (user_id, game_name))
    await conn.commit()

async def get_user_tracked_games(conn, user_id):
    async with conn.execute('''
        SELECT game_name, app_id, current_price, last_checked
        FROM game_trackers
        WHERE user_id = ?
    ''', (user_id,)) as cursor:
        return await cursor.fetchall()

async def update_game_price(conn, app_id, current_price, notified=False):
    if notified:
        await conn.execute('''
            UPDATE game_trackers
            SET current_price = ?, last_checked = CURRENT_TIMESTAMP, last_notified = CURRENT_TIMESTAMP
            WHERE app_id = ?
        ''', (current_price, app_id))
    else:
        await conn.execute('''
            UPDATE game_trackers
            SET current_price = ?, last_checked = CURRENT_TIMESTAMP
            WHERE app_id = ?
        ''', (current_price, app_id))
    await conn.commit()

async def get_tracked_games(conn):
    async with conn.execute('''
        SELECT DISTINCT app_id
        FROM game_trackers
        WHERE app_id IS NOT NULL
    ''') as cursor:
        return await cursor.fetchall()

async def get_users_tracking_game(conn, app_id):
    async with conn.execute('''
        SELECT DISTINCT user_id
        FROM game_trackers
        WHERE app_id = ?
    ''', (app_id,)) as cursor:
        return [row[0] for row in await cursor.fetchall()]

async def get_db_connection(db_name='database/chat_history.db'):
    conn = await db_connect(db_name)
    return conn

async def update_command_stats(conn, user_id: str, command_name: str):
    """Update the command usage statistics for a user."""
    try:
        await conn.execute('''
            INSERT INTO command_stats (user_id, command_name)
            VALUES (?, ?)
            ON CONFLICT(user_id, command_name) DO UPDATE SET
            usage_count = usage_count + 1,
            last_used = CURRENT_TIMESTAMP;
        ''', (user_id, command_name))
        await conn.commit()
    except Exception as e:
        logging.error(f"Failed to update command stats: {e}")

async def get_user_command_stats(conn, user_id: str):
    """Get command usage statistics for a specific user."""
    try:
        async with conn.execute('''
            SELECT command_name, usage_count, last_used
            FROM command_stats
            WHERE user_id = ?
            ORDER BY usage_count DESC;
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Failed to get user command stats: {e}")
        return []

async def get_command_stats(conn):
    """Get overall command usage statistics."""
    try:
        async with conn.execute('''
            SELECT command_name, SUM(usage_count) as total_uses, COUNT(DISTINCT user_id) as unique_users
            FROM command_stats
            GROUP BY command_name
            ORDER BY total_uses DESC;
        ''') as cursor:
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Failed to get command stats: {e}")
        return []

async def track_voice_join(conn, user_id: str, channel_id: str):
    """Track when a user joins a voice channel."""
    try:
        # First update or create stats record
        await conn.execute('''
            INSERT INTO voice_chat_stats (user_id, channel_id, join_count)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, channel_id) DO UPDATE SET
            join_count = join_count + 1;
        ''', (user_id, channel_id))
        
        # Then create session record
        await conn.execute('''
            INSERT OR REPLACE INTO voice_chat_sessions (user_id, channel_id, join_timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP);
        ''', (user_id, channel_id))
        
        await conn.commit()
    except Exception as e:
        logging.error(f"Failed to track voice join: {e}")

async def track_voice_leave(conn, user_id: str):
    """Track when a user leaves a voice channel and update their stats."""
    try:
        # Get session info
        async with conn.execute('''
            SELECT channel_id, join_timestamp
            FROM voice_chat_sessions
            WHERE user_id = ?;
        ''', (user_id,)) as cursor:
            session = await cursor.fetchone()
            
        if session:
            channel_id, join_time = session
            
            # Calculate duration
            await conn.execute('''
                UPDATE voice_chat_stats 
                SET leave_timestamp = CURRENT_TIMESTAMP,
                    duration = ROUND((JULIANDAY(CURRENT_TIMESTAMP) - JULIANDAY(?)) * 86400),
                    total_time = total_time + ROUND((JULIANDAY(CURRENT_TIMESTAMP) - JULIANDAY(?)) * 86400)
                WHERE user_id = ? AND channel_id = ?;
            ''', (join_time, join_time, user_id, channel_id))
            
            # Remove session
            await conn.execute('''
                DELETE FROM voice_chat_sessions
                WHERE user_id = ?;
            ''', (user_id,))
            
            await conn.commit()
    except Exception as e:
        logging.error(f"Failed to track voice leave: {e}")

async def get_user_voice_stats(conn, user_id: str):
    """Get voice chat statistics for a user."""
    try:
        async with conn.execute('''
            SELECT 
                channel_id,
                total_time,
                join_count,
                duration,
                join_timestamp,
                leave_timestamp
            FROM voice_chat_stats
            WHERE user_id = ?
            ORDER BY total_time DESC;
        ''', (user_id,)) as cursor:
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Failed to get user voice stats: {e}")
        return []

async def get_voice_leaderboard(conn):
    """Get overall voice chat leaderboard."""
    try:
        async with conn.execute('''
            SELECT 
                user_id,
                SUM(total_time) as total_time,
                SUM(join_count) as total_joins,
                COUNT(DISTINCT channel_id) as unique_channels
            FROM voice_chat_stats
            GROUP BY user_id
            ORDER BY total_time DESC;
        ''') as cursor:
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Failed to get voice leaderboard: {e}")
        return []
