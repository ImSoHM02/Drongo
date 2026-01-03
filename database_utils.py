import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from database_pool import get_main_pool, get_command_pool
import discord

class OptimizedDatabase:
    """
    Optimized database operations with batching, caching, and improved performance.
    """
    
    def __init__(self):
        self.batch_size = 100
        self.message_batch = []
        self.batch_lock = asyncio.Lock()
        
    async def add_missing_indexes(self):
        """Add missing database indexes for better performance."""
        pool = await get_main_pool()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_messages_user_guild ON messages (user_id, guild_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages (channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_messages_content_search ON messages (message_content)",
            "CREATE INDEX IF NOT EXISTS idx_voice_stats_user ON voice_chat_stats (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_voice_stats_channel ON voice_chat_stats (channel_id)",
            "CREATE INDEX IF NOT EXISTS idx_voice_sessions_user ON voice_chat_sessions (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_game_trackers_user ON game_trackers (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_game_trackers_app ON game_trackers (app_id)",
        ]
        
        for index_sql in indexes:
            try:
                await pool.execute_write(index_sql)
                logging.debug(f"Created index: {index_sql.split('idx_')[1].split(' ON')[0]}")
            except Exception as e:
                logging.error(f"Failed to create index: {e}")
    
    async def batch_store_messages(self, messages: List[Tuple]) -> int:
        """
        Store multiple messages in a single transaction for better performance.
        
        Args:
            messages: List of tuples (user_id, guild_id, channel_id, content, timestamp)
        
        Returns:
            Number of messages successfully stored
        """
        if not messages:
            return 0
            
        pool = await get_main_pool()
        
        try:
            # Use executemany for batch insert
            query = '''
                INSERT OR IGNORE INTO messages (user_id, guild_id, channel_id, message_content, timestamp)
                VALUES (?, ?, ?, ?, ?)
            '''
            
            await pool.execute_many(query, messages)
            logging.info(f"Batch stored {len(messages)} messages")
            return len(messages)
            
        except Exception as e:
            logging.error(f"Failed to batch store messages: {e}")
            return 0
    
    async def queue_message_for_batch(self, message: discord.Message, content: str):
        """Queue a message for batch processing."""
        async with self.batch_lock:
            self.message_batch.append((
                str(message.author.id),
                str(message.guild.id),
                str(message.channel.id),
                content,
                message.created_at.isoformat()
            ))
            
            # Process batch if it's full
            if len(self.message_batch) >= self.batch_size:
                await self._process_message_batch()
    
    async def _process_message_batch(self):
        """Process the current message batch."""
        if not self.message_batch:
            return
            
        batch = self.message_batch.copy()
        self.message_batch.clear()
        
        # Process batch in background
        asyncio.create_task(self.batch_store_messages(batch))
    
    async def flush_message_batch(self):
        """Flush any remaining messages in the batch."""
        async with self.batch_lock:
            if self.message_batch:
                await self._process_message_batch()
    
    async def get_user_message_stats(self, user_id: str, guild_id: str) -> Dict[str, Any]:
        """
        Get comprehensive message statistics for a user.
        Uses optimized queries with proper indexing.
        """
        pool = await get_main_pool()
        
        # Get basic message count
        total_messages = await pool.execute_single(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND guild_id = ?",
            (user_id, guild_id)
        )
        
        # Get messages in last 7 days
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_messages = await pool.execute_single(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND guild_id = ? AND timestamp > ?",
            (user_id, guild_id, week_ago)
        )
        
        # Get most active channel
        most_active_channel = await pool.execute_single(
            """
            SELECT channel_id, COUNT(*) as count 
            FROM messages 
            WHERE user_id = ? AND guild_id = ? 
            GROUP BY channel_id 
            ORDER BY count DESC 
            LIMIT 1
            """,
            (user_id, guild_id)
        )
        
        return {
            'total_messages': total_messages[0] if total_messages else 0,
            'recent_messages': recent_messages[0] if recent_messages else 0,
            'most_active_channel': most_active_channel[0] if most_active_channel else None,
            'channel_message_count': most_active_channel[1] if most_active_channel else 0
        }
    
    async def get_server_activity_summary(self, guild_id: str) -> Dict[str, Any]:
        """Get server activity summary with optimized queries."""
        pool = await get_main_pool()
        
        # Total messages
        total_messages = await pool.execute_single(
            "SELECT COUNT(*) FROM messages WHERE guild_id = ?",
            (guild_id,)
        )
        
        # Unique users
        unique_users = await pool.execute_single(
            "SELECT COUNT(DISTINCT user_id) FROM messages WHERE guild_id = ?",
            (guild_id,)
        )
        
        # Messages today
        today = datetime.now().date().isoformat()
        today_messages = await pool.execute_single(
            "SELECT COUNT(*) FROM messages WHERE guild_id = ? AND DATE(timestamp) = ?",
            (guild_id, today)
        )
        
        # Top 5 active users
        top_users = await pool.execute_query(
            """
            SELECT user_id, COUNT(*) as message_count
            FROM messages 
            WHERE guild_id = ?
            GROUP BY user_id
            ORDER BY message_count DESC
            LIMIT 5
            """,
            (guild_id,)
        )
        
        return {
            'total_messages': total_messages[0] if total_messages else 0,
            'unique_users': unique_users[0] if unique_users else 0,
            'today_messages': today_messages[0] if today_messages else 0,
            'top_users': top_users
        }
    
    async def cleanup_old_data(self, days_to_keep: int = 365):
        """
        Clean up old data to prevent database bloat.
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        pool = await get_main_pool()
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
        
        # Clean up old messages
        _, deleted_messages = await pool.execute_write(
            "DELETE FROM messages WHERE timestamp < ?",
            (cutoff_date,)
        )
        
        # Clean up old voice stats
        _, deleted_voice = await pool.execute_write(
            "DELETE FROM voice_chat_stats WHERE join_timestamp < ?",
            (cutoff_date,)
        )
        
        # Vacuum to reclaim space
        await pool.execute_write("VACUUM")
        
        logging.info(f"Cleaned up {deleted_messages} old messages and {deleted_voice} voice records")
        
        return {
            'deleted_messages': deleted_messages,
            'deleted_voice_records': deleted_voice
        }
    
    async def get_word_usage_optimized(self, guild_id: str, word: str, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Optimized word usage query using full-text search if available.
        """
        pool = await get_main_pool()
        
        # Use LIKE with wildcards for simple word matching
        # In a production system, consider implementing FTS (Full-Text Search)
        word_pattern = f'%{word.lower()}%'
        
        results = await pool.execute_query(
            """
            SELECT user_id, COUNT(*) as usage_count
            FROM messages 
            WHERE guild_id = ? AND LOWER(message_content) LIKE ?
            GROUP BY user_id
            ORDER BY usage_count DESC
            LIMIT ?
            """,
            (guild_id, word_pattern, limit)
        )
        
        return results
    
    async def analyze_database_health(self) -> Dict[str, Any]:
        """Analyze database health and performance metrics."""
        pool = await get_main_pool()
        
        # Get table sizes
        table_info = await pool.execute_query(
            """
            SELECT name, 
                   (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=m.name) as table_count
            FROM sqlite_master m WHERE type='table'
            """
        )
        
        # Get database size info
        page_count = await pool.execute_single("PRAGMA page_count")
        page_size = await pool.execute_single("PRAGMA page_size")
        
        if page_count and page_size:
            db_size_bytes = page_count[0] * page_size[0]
            db_size_mb = db_size_bytes / (1024 * 1024)
        else:
            db_size_mb = 0
        
        # Check for any index usage
        index_list = await pool.execute_query("SELECT name FROM sqlite_master WHERE type='index'")
        
        return {
            'database_size_mb': round(db_size_mb, 2),
            'table_count': len(table_info),
            'index_count': len(index_list),
            'tables': [table[0] for table in table_info],
            'indexes': [index[0] for index in index_list if not index[0].startswith('sqlite_')]
        }

# Global instance
optimized_db = OptimizedDatabase()

# Convenience functions for backward compatibility
async def initialize_database_optimizations():
    """Initialize database optimizations."""
    await optimized_db.add_missing_indexes()
    logging.info("Database optimizations initialized")

async def batch_store_message(message: discord.Message, content: str):
    """Queue message for batch storage."""
    await optimized_db.queue_message_for_batch(message, content)

async def flush_pending_messages():
    """Flush any pending message batches."""
    await optimized_db.flush_message_batch()