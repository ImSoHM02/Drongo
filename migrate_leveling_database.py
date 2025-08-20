#!/usr/bin/env python3
"""
Leveling System Database Migration Script for Drongo Bot.
Creates tables, indexes, triggers, and views for the XP/leveling system.
"""

import asyncio
import logging
import sys
import os
from database_pool import get_main_pool
from database_utils import optimized_db

async def create_leveling_tables():
    """Create all leveling system tables with proper constraints and relationships."""
    pool = await get_main_pool()
    
    logging.info("Creating leveling system tables...")
    
    # User Levels Table
    await pool.execute_write('''
        CREATE TABLE IF NOT EXISTS user_levels (
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            current_xp INTEGER NOT NULL DEFAULT 0,
            current_level INTEGER NOT NULL DEFAULT 0,
            total_xp INTEGER NOT NULL DEFAULT 0,
            messages_sent INTEGER NOT NULL DEFAULT 0,
            last_xp_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            daily_xp_earned INTEGER NOT NULL DEFAULT 0,
            daily_reset_date TEXT DEFAULT (date('now')),
            level_up_timestamp TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        );
    ''')
    
    # XP Transactions Table
    await pool.execute_write('''
        CREATE TABLE IF NOT EXISTS xp_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            message_id TEXT,
            xp_awarded INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT 'message',
            message_length INTEGER,
            word_count INTEGER,
            char_count INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            daily_cap_applied BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id, guild_id) REFERENCES user_levels(user_id, guild_id)
        );
    ''')
    
    # Leveling Configuration Table
    await pool.execute_write('''
        CREATE TABLE IF NOT EXISTS leveling_config (
            guild_id TEXT PRIMARY KEY,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            base_xp INTEGER NOT NULL DEFAULT 5,
            max_xp INTEGER NOT NULL DEFAULT 25,
            word_multiplier REAL NOT NULL DEFAULT 0.5,
            char_multiplier REAL NOT NULL DEFAULT 0.1,
            min_cooldown_seconds INTEGER NOT NULL DEFAULT 30,
            max_cooldown_seconds INTEGER NOT NULL DEFAULT 60,
            min_message_chars INTEGER NOT NULL DEFAULT 5,
            min_message_words INTEGER NOT NULL DEFAULT 2,
            daily_xp_cap INTEGER NOT NULL DEFAULT 1000,
            blacklisted_channels TEXT DEFAULT '[]',
            whitelisted_channels TEXT DEFAULT '[]',
            level_up_announcements BOOLEAN NOT NULL DEFAULT TRUE,
            announcement_channel_id TEXT,
            dm_level_notifications BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    # Rank Titles Table
    await pool.execute_write('''
        CREATE TABLE IF NOT EXISTS rank_titles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            min_level INTEGER NOT NULL,
            max_level INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            color_hex TEXT DEFAULT '#7289DA',
            emoji TEXT,
            role_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, min_level),
            FOREIGN KEY (guild_id) REFERENCES leveling_config(guild_id)
        );
    ''')
    
    # Level Rewards Table
    await pool.execute_write('''
        CREATE TABLE IF NOT EXISTS level_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            level INTEGER NOT NULL,
            reward_type TEXT NOT NULL CHECK (reward_type IN ('role', 'custom_message', 'xp_bonus', 'milestone')),
            reward_data TEXT NOT NULL,
            is_milestone BOOLEAN DEFAULT FALSE,
            milestone_interval INTEGER,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, level, reward_type),
            FOREIGN KEY (guild_id) REFERENCES leveling_config(guild_id)
        );
    ''')
    
    # XP Cooldowns Table
    await pool.execute_write('''
        CREATE TABLE IF NOT EXISTS xp_cooldowns (
            user_id TEXT NOT NULL,
            guild_id TEXT NOT NULL,
            last_xp_message_id TEXT,
            last_xp_timestamp TIMESTAMP NOT NULL,
            cooldown_ends_at TIMESTAMP NOT NULL,
            consecutive_messages INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, guild_id),
            FOREIGN KEY (user_id, guild_id) REFERENCES user_levels(user_id, guild_id)
        );
    ''')
    
    logging.info("Leveling system tables created successfully")

async def create_leveling_indexes():
    """Create performance indexes for the leveling system."""
    pool = await get_main_pool()
    
    logging.info("Creating leveling system indexes...")
    
    indexes = [
        # User Levels Indexes
        "CREATE INDEX IF NOT EXISTS idx_user_levels_guild_level ON user_levels (guild_id, current_level DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_levels_guild_xp ON user_levels (guild_id, total_xp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_user_levels_daily_reset ON user_levels (daily_reset_date)",
        "CREATE INDEX IF NOT EXISTS idx_user_levels_updated ON user_levels (updated_at)",
        
        # XP Transactions Indexes
        "CREATE INDEX IF NOT EXISTS idx_xp_transactions_user_guild ON xp_transactions (user_id, guild_id)",
        "CREATE INDEX IF NOT EXISTS idx_xp_transactions_timestamp ON xp_transactions (timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_xp_transactions_channel ON xp_transactions (channel_id, timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_xp_transactions_reason ON xp_transactions (reason, timestamp DESC)",
        
        # Rank Titles Indexes
        "CREATE INDEX IF NOT EXISTS idx_rank_titles_guild_level ON rank_titles (guild_id, min_level)",
        "CREATE INDEX IF NOT EXISTS idx_rank_titles_role ON rank_titles (guild_id, role_id) WHERE role_id IS NOT NULL",
        
        # Level Rewards Indexes
        "CREATE INDEX IF NOT EXISTS idx_level_rewards_guild_level ON level_rewards (guild_id, level)",
        "CREATE INDEX IF NOT EXISTS idx_level_rewards_type ON level_rewards (guild_id, reward_type)",
        "CREATE INDEX IF NOT EXISTS idx_level_rewards_active ON level_rewards (guild_id, active) WHERE active = TRUE",
        "CREATE INDEX IF NOT EXISTS idx_level_rewards_milestone ON level_rewards (guild_id, is_milestone, milestone_interval) WHERE is_milestone = TRUE",
        
        # XP Cooldowns Indexes
        "CREATE INDEX IF NOT EXISTS idx_xp_cooldowns_ends_at ON xp_cooldowns (cooldown_ends_at)",
        "CREATE INDEX IF NOT EXISTS idx_xp_cooldowns_timestamp ON xp_cooldowns (last_xp_timestamp)",
    ]
    
    for index_sql in indexes:
        try:
            await pool.execute_write(index_sql)
            index_name = index_sql.split("idx_")[1].split(" ON")[0]
            logging.info(f"Created index: {index_name}")
        except Exception as e:
            logging.error(f"Failed to create index: {e}")
    
    logging.info("Leveling system indexes created successfully")

async def create_leveling_triggers():
    """Create database triggers for auto-updates."""
    pool = await get_main_pool()
    
    logging.info("Creating leveling system triggers...")
    
    triggers = [
        # Update timestamp trigger for user_levels
        '''
        CREATE TRIGGER IF NOT EXISTS trigger_user_levels_updated_at
            AFTER UPDATE ON user_levels
            FOR EACH ROW
            BEGIN
                UPDATE user_levels SET updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = NEW.user_id AND guild_id = NEW.guild_id;
            END;
        ''',
        
        # Update timestamp trigger for leveling_config
        '''
        CREATE TRIGGER IF NOT EXISTS trigger_leveling_config_updated_at
            AFTER UPDATE ON leveling_config
            FOR EACH ROW
            BEGIN
                UPDATE leveling_config SET updated_at = CURRENT_TIMESTAMP 
                WHERE guild_id = NEW.guild_id;
            END;
        ''',
        
        # Daily XP reset trigger
        '''
        CREATE TRIGGER IF NOT EXISTS trigger_daily_xp_reset
            AFTER UPDATE ON user_levels
            FOR EACH ROW
            WHEN NEW.daily_reset_date != date('now')
            BEGIN
                UPDATE user_levels 
                SET daily_xp_earned = 0, daily_reset_date = date('now')
                WHERE user_id = NEW.user_id AND guild_id = NEW.guild_id;
            END;
        '''
    ]
    
    for trigger_sql in triggers:
        try:
            await pool.execute_write(trigger_sql)
            trigger_name = trigger_sql.split("trigger_")[1].split("\n")[0].strip()
            logging.info(f"Created trigger: {trigger_name}")
        except Exception as e:
            logging.error(f"Failed to create trigger: {e}")
    
    logging.info("Leveling system triggers created successfully")

async def create_leveling_views():
    """Create database views for common queries."""
    pool = await get_main_pool()
    
    logging.info("Creating leveling system views...")
    
    views = [
        # Leaderboard view
        '''
        CREATE VIEW IF NOT EXISTS view_xp_leaderboard AS
        SELECT 
            user_id,
            guild_id,
            current_level,
            current_xp,
            total_xp,
            messages_sent,
            RANK() OVER (PARTITION BY guild_id ORDER BY total_xp DESC) as rank,
            ROW_NUMBER() OVER (PARTITION BY guild_id ORDER BY total_xp DESC) as position
        FROM user_levels
        WHERE current_level > 0 OR total_xp > 0;
        ''',
        
        # User ranks with titles view
        '''
        CREATE VIEW IF NOT EXISTS view_user_ranks AS
        SELECT 
            ul.user_id,
            ul.guild_id,
            ul.current_level,
            ul.current_xp,
            ul.total_xp,
            rt.title as rank_title,
            rt.description as rank_description,
            rt.color_hex,
            rt.emoji,
            rt.role_id as rank_role_id
        FROM user_levels ul
        LEFT JOIN rank_titles rt ON 
            ul.guild_id = rt.guild_id 
            AND ul.current_level >= rt.min_level 
            AND (rt.max_level IS NULL OR ul.current_level <= rt.max_level)
        WHERE rt.id = (
            SELECT id FROM rank_titles rt2 
            WHERE rt2.guild_id = ul.guild_id 
            AND ul.current_level >= rt2.min_level
            AND (rt2.max_level IS NULL OR ul.current_level <= rt2.max_level)
            ORDER BY rt2.min_level DESC LIMIT 1
        );
        ''',
        
        # Recent activity view
        '''
        CREATE VIEW IF NOT EXISTS view_recent_xp_activity AS
        SELECT 
            xt.user_id,
            xt.guild_id,
            xt.channel_id,
            xt.xp_awarded,
            xt.reason,
            xt.timestamp,
            ul.current_level,
            ul.current_xp
        FROM xp_transactions xt
        JOIN user_levels ul ON xt.user_id = ul.user_id AND xt.guild_id = ul.guild_id
        WHERE xt.timestamp >= datetime('now', '-24 hours')
        ORDER BY xt.timestamp DESC;
        '''
    ]
    
    for view_sql in views:
        try:
            await pool.execute_write(view_sql)
            view_name = view_sql.split("view_")[1].split(" AS")[0]
            logging.info(f"Created view: {view_name}")
        except Exception as e:
            logging.error(f"Failed to create view: {e}")
    
    logging.info("Leveling system views created successfully")

async def insert_default_config():
    """Insert default configuration for guilds that don't have leveling config."""
    pool = await get_main_pool()
    
    logging.info("Setting up default leveling configurations...")
    
    # This would typically be called per-guild when leveling is first enabled
    # For migration, we'll just ensure the table structure is ready
    logging.info("Default configuration structure ready")

async def verify_leveling_migration():
    """Verify that the leveling migration was successful."""
    pool = await get_main_pool()
    
    logging.info("Verifying leveling system migration...")
    
    # Check that all tables exist
    tables_to_check = [
        'user_levels',
        'xp_transactions',
        'leveling_config',
        'rank_titles',
        'level_rewards',
        'xp_cooldowns'
    ]
    
    for table in tables_to_check:
        result = await pool.execute_single(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if result:
            logging.info(f"✓ Table {table} exists")
        else:
            logging.error(f"✗ Table {table} missing")
            return False
    
    # Check that views exist
    views_to_check = [
        'view_xp_leaderboard',
        'view_user_ranks',
        'view_recent_xp_activity'
    ]
    
    for view in views_to_check:
        result = await pool.execute_single(
            "SELECT name FROM sqlite_master WHERE type='view' AND name=?",
            (view,)
        )
        if result:
            logging.info(f"✓ View {view} exists")
        else:
            logging.error(f"✗ View {view} missing")
            return False
    
    # Test basic operations
    try:
        # Test inserting a configuration
        await pool.execute_write(
            "INSERT OR IGNORE INTO leveling_config (guild_id) VALUES (?)",
            ("test_guild_123",)
        )
        
        # Test querying
        result = await pool.execute_single(
            "SELECT enabled FROM leveling_config WHERE guild_id = ?",
            ("test_guild_123",)
        )
        
        if result and result[0] == 1:  # Boolean true is 1 in SQLite
            logging.info("✓ Basic operations working")
        else:
            logging.error("✗ Basic operations failed")
            return False
            
        # Clean up test data
        await pool.execute_write(
            "DELETE FROM leveling_config WHERE guild_id = ?",
            ("test_guild_123",)
        )
        
    except Exception as e:
        logging.error(f"✗ Basic operations test failed: {e}")
        return False
    
    logging.info("Leveling system migration verified successfully")
    return True

async def migrate_leveling_database():
    """Main migration function for the leveling system."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("Drongo Bot Leveling System Migration")
    print("=====================================\n")
    
    try:
        # Ensure database directory exists
        os.makedirs('database', exist_ok=True)
        
        # Create all leveling tables
        await create_leveling_tables()
        
        # Create indexes for performance
        await create_leveling_indexes()
        
        # Create triggers for auto-updates
        await create_leveling_triggers()
        
        # Create views for common queries
        await create_leveling_views()
        
        # Set up default configurations
        await insert_default_config()
        
        # Verify migration
        success = await verify_leveling_migration()
        
        if success:
            print("\n✓ Leveling system migration completed successfully!")
            print("The following components were created:")
            print("  • user_levels - User XP and level progression")
            print("  • xp_transactions - XP award audit log")
            print("  • leveling_config - Guild-specific settings")
            print("  • rank_titles - Custom rank names and roles")
            print("  • xp_cooldowns - Anti-abuse cooldown tracking")
            print("  • Performance indexes and triggers")
            print("  • Database views for common queries")
            return True
        else:
            print("\n✗ Migration verification failed!")
            return False
            
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        logging.error(f"Migration error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(migrate_leveling_database())
    if not success:
        sys.exit(1)