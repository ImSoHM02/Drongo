import aiosqlite
import asyncio
import logging
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager
import os

DEFAULT_MAIN_DB_PATH = os.getenv("DRONGO_MAIN_DB_PATH", "database/chat_history.db")
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

# Backward compatibility functions
async def get_db_connection(db_name='database/chat_history.db'):
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
