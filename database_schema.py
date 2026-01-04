# Guild Chat History Database Schema Definitions

# Global configuration database schema
GUILD_CONFIG_SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id TEXT PRIMARY KEY,
    guild_name TEXT NOT NULL,
    logging_enabled INTEGER DEFAULT 1,
    date_joined TEXT NOT NULL,
    last_updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS historical_fetch_progress (
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    last_fetched_message_id TEXT,
    oldest_message_id TEXT,
    total_fetched INTEGER DEFAULT 0,
    fetch_completed INTEGER DEFAULT 0,
    is_scanning INTEGER DEFAULT 0,
    last_fetch_timestamp TEXT,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS fetch_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    priority INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_fetch_queue_status
ON fetch_queue (status, priority DESC, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_fetch_progress_guild
ON historical_fetch_progress (guild_id, is_scanning);
"""

# Per-guild database schema (chat history only)
PER_GUILD_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message_content TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS last_message (
    channel_id TEXT PRIMARY KEY,
    last_message_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embed_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    inline BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (message_id) REFERENCES messages (id)
);

CREATE INDEX IF NOT EXISTS idx_messages_lookup
ON messages (guild_id, channel_id, user_id, message_content);

CREATE INDEX IF NOT EXISTS idx_messages_timestamp
ON messages (timestamp);

CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp
ON messages (channel_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_embed_fields_message
ON embed_fields (message_id);
"""

# Database paths
def get_guild_config_db_path():
    """Get path to global guild configuration database"""
    return 'database/guild_config.db'

def get_guild_db_path(guild_id):
    """Get path to guild-specific database"""
    return f'database/{guild_id}/chat_history.db'

def get_guild_db_dir(guild_id):
    """Get directory path for guild database"""
    return f'database/{guild_id}'
