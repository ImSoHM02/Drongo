import aiosqlite
import logging

async def db_connect():
    """Connect to the command stats database."""
    return await aiosqlite.connect('database/command_stats.db')

async def create_tables(conn):
    """Create the necessary tables for command statistics."""
    try:
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
        await conn.commit()
    except Exception as e:
        logging.error(f"An error occurred while creating command stats tables: {e}")

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
