# Guild Chat History Database Schema Definitions

# Global configuration database schema
GUILD_CONFIG_SCHEMA = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id TEXT PRIMARY KEY,
    guild_name TEXT NOT NULL,
    logging_enabled INTEGER DEFAULT 1,
    bot_name TEXT DEFAULT 'drongo',
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
    discord_message_id TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_messages_lookup
ON messages (guild_id, channel_id, user_id, message_content);

CREATE INDEX IF NOT EXISTS idx_messages_timestamp
ON messages (timestamp);

CREATE INDEX IF NOT EXISTS idx_messages_channel_timestamp
ON messages (channel_id, timestamp DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_discord_id
ON messages (discord_message_id);
"""

# Attachments database schema (per-guild)
ATTACHMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    url TEXT NOT NULL,
    filename TEXT,
    content_type TEXT,
    size_bytes INTEGER,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attachments_message
ON attachments (message_id);

CREATE INDEX IF NOT EXISTS idx_attachments_user
ON attachments (user_id, guild_id);

CREATE INDEX IF NOT EXISTS idx_attachments_type
ON attachments (content_type);
"""

# Embeds database schema (per-guild)
EMBEDS_SCHEMA = """
CREATE TABLE IF NOT EXISTS embeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    embed_type TEXT,
    title TEXT,
    description TEXT,
    url TEXT,
    color INTEGER,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS embed_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    embed_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    inline BOOLEAN NOT NULL DEFAULT 0,
    FOREIGN KEY (embed_id) REFERENCES embeds (id)
);

CREATE TABLE IF NOT EXISTS embed_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    embed_id INTEGER NOT NULL,
    image_url TEXT,
    thumbnail_url TEXT,
    FOREIGN KEY (embed_id) REFERENCES embeds (id)
);

CREATE INDEX IF NOT EXISTS idx_embeds_message
ON embeds (message_id);

CREATE INDEX IF NOT EXISTS idx_embeds_user
ON embeds (user_id, guild_id);

CREATE INDEX IF NOT EXISTS idx_embed_fields_embed
ON embed_fields (embed_id);

CREATE INDEX IF NOT EXISTS idx_embed_images_embed
ON embed_images (embed_id);
-- URLs now live in the same database file as embeds for simpler lookups
CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    url_position INTEGER,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_urls_message
ON urls (message_id);

CREATE INDEX IF NOT EXISTS idx_urls_user
ON urls (user_id, guild_id);

CREATE INDEX IF NOT EXISTS idx_urls_domain
ON urls (domain);
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

def get_attachments_db_path(guild_id):
    """Get path to guild-specific attachments database"""
    return f'database/{guild_id}/attachments.db'

def get_embeds_db_path(guild_id):
    """Get path to guild-specific embeds database"""
    return f'database/{guild_id}/embeds.db'

def get_urls_db_path(guild_id):
    """
    URLs are stored alongside embeds; keep this helper for backward compatibility.
    """
    return get_embeds_db_path(guild_id)
