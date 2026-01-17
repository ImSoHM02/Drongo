import aiosqlite
import asyncio
import logging
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager
import os

DEFAULT_MAIN_DB_PATH = os.getenv("DRONGO_MAIN_DB_PATH", "database/system.db")
DEFAULT_LEVELING_DB_PATH = os.getenv("DRONGO_LEVELING_DB_PATH", "database/leveling_system.db")

class DatabasePool:
    """
    A simple database connection pool for SQLite using aiosqlite.
    Manages multiple database connections to reduce connection overhead.
    """
    
    def __init__(self, db_path: str = DEFAULT_MAIN_DB_PATH, pool_size: int = 10):
        self.db_path = db_path
        self.pool_size = pool_size
        self._pool: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self._total_connections = 0
        self._initialized = False
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize the connection pool with pre-created connections."""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:  # Double-check locking
                return
                
            # Ensure database directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create initial connections
            for _ in range(self.pool_size):
                conn = await aiosqlite.connect(self.db_path)
                # Enable WAL mode for better concurrency
                await conn.execute('PRAGMA journal_mode=WAL')
                # Set reasonable timeout
                await conn.execute('PRAGMA busy_timeout=30000')
                # Enable foreign key constraints
                await conn.execute('PRAGMA foreign_keys=ON')
                await conn.commit()
                await self._pool.put(conn)
                self._total_connections += 1
                
            self._initialized = True
            logging.info(f"Database pool initialized with {self.pool_size} connections")
    
    async def _create_connection(self) -> aiosqlite.Connection:
        """Create a new database connection with optimal settings."""
        conn = await aiosqlite.connect(self.db_path)
        await conn.execute('PRAGMA journal_mode=WAL')
        await conn.execute('PRAGMA busy_timeout=30000')
        await conn.execute('PRAGMA foreign_keys=ON')
        await conn.commit()
        return conn
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[aiosqlite.Connection]:
        """
        Get a database connection from the pool.
        Automatically returns the connection to the pool when done.
        """
        if not self._initialized:
            await self.initialize()
            
        try:
            # Try to get connection from pool (non-blocking)
            conn = self._pool.get_nowait()
        except asyncio.QueueEmpty:
            # Pool is empty, create a temporary connection
            logging.warning("Connection pool exhausted, creating temporary connection")
            conn = await self._create_connection()
            temp_connection = True
        else:
            temp_connection = False
            
        try:
            yield conn
        except Exception as e:
            # Log the error but don't re-raise here
            logging.error(f"Database operation error: {e}")
            raise
        finally:
            if temp_connection:
                # Close temporary connection
                await conn.close()
            else:
                # Return connection to pool
                try:
                    self._pool.put_nowait(conn)
                except asyncio.QueueFull:
                    # This shouldn't happen, but close the connection if pool is somehow full
                    await conn.close()
                    logging.error("Connection pool full when returning connection")
    
    async def execute_query(self, query: str, params=None):
        """Execute a query and return results."""
        async with self.get_connection() as conn:
            async with conn.execute(query, params or ()) as cursor:
                return await cursor.fetchall()
    
    async def execute_single(self, query: str, params=None):
        """Execute a query and return a single result."""
        async with self.get_connection() as conn:
            async with conn.execute(query, params or ()) as cursor:
                return await cursor.fetchone()
    
    async def execute_write(self, query: str, params=None):
        """Execute a write query (INSERT, UPDATE, DELETE)."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            await conn.commit()
            return cursor.lastrowid, cursor.rowcount
    
    async def execute_many(self, query: str, param_list):
        """Execute multiple queries with different parameters."""
        async with self.get_connection() as conn:
            await conn.executemany(query, param_list)
            await conn.commit()
    
    async def close_all(self):
        """Close all connections in the pool."""
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                await conn.close()
            except asyncio.QueueEmpty:
                break
        
        self._total_connections = 0
        self._initialized = False
        logging.info("Database pool closed")

# Global pool instances
_main_pool: Optional[DatabasePool] = None
_command_pool: Optional[DatabasePool] = None
_leveling_pool: Optional[DatabasePool] = None

async def get_main_pool() -> DatabasePool:
    """Get the main database connection pool."""
    global _main_pool
    if _main_pool is None:
        _main_pool = DatabasePool(DEFAULT_MAIN_DB_PATH)
        await _main_pool.initialize()
    return _main_pool

async def get_command_pool() -> DatabasePool:
    """Get the command database connection pool."""
    global _command_pool
    if _command_pool is None:
        _command_pool = DatabasePool('database/command_stats.db')
        await _command_pool.initialize()
    return _command_pool

async def get_leveling_pool() -> DatabasePool:
    """Get the leveling system database connection pool."""
    global _leveling_pool
    if _leveling_pool is None:
        _leveling_pool = DatabasePool(DEFAULT_LEVELING_DB_PATH)
        await _leveling_pool.initialize()
    return _leveling_pool

async def close_all_pools():
    """Close all database pools."""
    global _main_pool, _command_pool, _leveling_pool
    if _main_pool:
        await _main_pool.close_all()
        _main_pool = None
    if _command_pool:
        await _command_pool.close_all()
        _command_pool = None
    if _leveling_pool:
        await _leveling_pool.close_all()
        _leveling_pool = None

# Multi-guild database pool management
from time import time
from .database_schema import get_guild_config_db_path, get_guild_db_path

class MultiGuildDatabasePool:
    """
    Manages database pools for multiple guilds with LRU eviction.
    """

    def __init__(self, max_pools: int = 20, pool_timeout: int = 1800):
        self.max_pools = max_pools
        self.pool_timeout = pool_timeout  # 30 minutes default
        self.guild_pools = {}  # guild_id -> DatabasePool
        self.last_accessed = {}  # guild_id -> timestamp
        self.config_pool: Optional[DatabasePool] = None
        self._lock = asyncio.Lock()

    async def initialize_config_pool(self):
        """Initialize the global configuration database pool."""
        if self.config_pool is None:
            config_db_path = get_guild_config_db_path()
            self.config_pool = DatabasePool(config_db_path, pool_size=5)
            await self.config_pool.initialize()
            logging.info("Initialized guild configuration database pool")

    @asynccontextmanager
    async def get_config_connection(self) -> AsyncContextManager[aiosqlite.Connection]:
        """Get a connection to the global configuration database."""
        if self.config_pool is None:
            await self.initialize_config_pool()

        async with self.config_pool.get_connection() as conn:
            yield conn

    async def get_guild_pool(self, guild_id: str) -> DatabasePool:
        """
        Get or create a database pool for a specific guild.
        Implements LRU eviction when max_pools is reached.
        """
        async with self._lock:
            # Update last accessed time
            self.last_accessed[guild_id] = time()

            # Return existing pool if available
            if guild_id in self.guild_pools:
                return self.guild_pools[guild_id]

            # Check if we need to evict a pool
            if len(self.guild_pools) >= self.max_pools:
                await self._evict_least_recently_used_pool()

            # Create new pool
            guild_db_path = get_guild_db_path(guild_id)
            pool = DatabasePool(guild_db_path, pool_size=5)
            await pool.initialize()

            self.guild_pools[guild_id] = pool
            logging.info(f"Created database pool for guild {guild_id}")

            return pool

    @asynccontextmanager
    async def get_guild_connection(self, guild_id: str) -> AsyncContextManager[aiosqlite.Connection]:
        """Get a connection to a guild-specific database."""
        pool = await self.get_guild_pool(guild_id)
        async with pool.get_connection() as conn:
            yield conn

    async def _evict_least_recently_used_pool(self):
        """Evict the least recently used guild pool."""
        if not self.guild_pools:
            return

        # Find LRU guild
        lru_guild_id = min(self.last_accessed, key=self.last_accessed.get)

        # Close and remove pool
        pool = self.guild_pools.pop(lru_guild_id)
        await pool.close_all()
        self.last_accessed.pop(lru_guild_id)

        logging.info(f"Evicted database pool for guild {lru_guild_id} (LRU)")

    async def cleanup_inactive_pools(self):
        """Clean up pools that haven't been accessed in a while."""
        current_time = time()

        async with self._lock:
            inactive_guilds = [
                guild_id for guild_id, last_time in self.last_accessed.items()
                if current_time - last_time > self.pool_timeout
            ]

            for guild_id in inactive_guilds:
                if guild_id in self.guild_pools:
                    pool = self.guild_pools.pop(guild_id)
                    await pool.close_all()
                    self.last_accessed.pop(guild_id)
                    logging.info(f"Closed inactive database pool for guild {guild_id}")

    async def close_all(self):
        """Close all guild pools and the config pool."""
        async with self._lock:
            for pool in self.guild_pools.values():
                await pool.close_all()

            self.guild_pools.clear()
            self.last_accessed.clear()

            if self.config_pool:
                await self.config_pool.close_all()
                self.config_pool = None

        logging.info("Closed all guild database pools")

# Global multi-guild pool instance
_multi_guild_pool: Optional[MultiGuildDatabasePool] = None

async def get_multi_guild_pool() -> MultiGuildDatabasePool:
    """Get the global multi-guild database pool."""
    global _multi_guild_pool
    if _multi_guild_pool is None:
        max_pools = int(os.getenv("CHAT_HISTORY_MAX_POOLS", "20"))
        pool_timeout = int(os.getenv("CHAT_HISTORY_POOL_TIMEOUT", "1800"))
        _multi_guild_pool = MultiGuildDatabasePool(max_pools=max_pools, pool_timeout=pool_timeout)
        await _multi_guild_pool.initialize_config_pool()
    return _multi_guild_pool

async def get_guild_db_connection(guild_id: str) -> AsyncContextManager[aiosqlite.Connection]:
    """Get a connection to a guild-specific database."""
    pool = await get_multi_guild_pool()
    return pool.get_guild_connection(guild_id)

async def get_config_db_connection() -> AsyncContextManager[aiosqlite.Connection]:
    """Get a connection to the guild configuration database."""
    pool = await get_multi_guild_pool()
    return pool.get_config_connection()

# Backward compatibility functions
async def get_db_connection(db_name='database/system.db'):
    """
    Backward compatibility function.
    Returns a connection from the appropriate pool.
    """
    normalized_name = os.path.normpath(db_name)
    base_name = os.path.basename(normalized_name)

    if base_name and 'command_stats' in base_name:
        pool = await get_command_pool()
    elif os.path.normpath(DEFAULT_LEVELING_DB_PATH) == normalized_name or 'leveling' in base_name:
        pool = await get_leveling_pool()
    else:
        pool = await get_main_pool()

    # For backward compatibility, return a connection that will be managed by the caller
    # This is not ideal but maintains compatibility
    async with pool.get_connection() as conn:
        # Create a new connection for backward compatibility
        # This defeats the purpose of pooling but maintains API compatibility
        dir_name = os.path.dirname(db_name)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        new_conn = await aiosqlite.connect(db_name)
        await new_conn.execute('PRAGMA journal_mode=WAL')
        await new_conn.execute('PRAGMA busy_timeout=30000')
        await new_conn.execute('PRAGMA foreign_keys=ON')
        return new_conn
