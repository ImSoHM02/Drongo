#!/usr/bin/env python3
"""
Database migration script for Drongo bot.
Applies database optimizations and indexes to existing databases.
"""

import asyncio
import logging
import sys
from database_utils import optimized_db
from database_pool import get_main_pool, get_command_pool

async def migrate_database():
    """Apply database migrations and optimizations."""
    logging.basicConfig(level=logging.INFO)
    
    print("Starting database migration...")
    
    try:
        # Initialize connection pools
        print("Initializing connection pools...")
        main_pool = await get_main_pool()
        command_pool = await get_command_pool()
        
        # Add missing indexes
        print("Adding database indexes...")
        await optimized_db.add_missing_indexes()
        
        # Analyze current database health
        print("Analyzing database health...")
        health = await optimized_db.analyze_database_health()
        
        print(f"Migration completed successfully!")
        print(f"Database size: {health['database_size_mb']} MB")
        print(f"Tables: {health['table_count']}")
        print(f"Indexes: {health['index_count']}")
        
        if health.get('indexes'):
            print("Custom indexes created:")
            for index in health['indexes']:
                print(f"  - {index}")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        logging.error(f"Migration error: {e}", exc_info=True)
        return False
    
    return True

async def verify_migration():
    """Verify that migration was successful."""
    print("\nVerifying migration...")
    
    try:
        pool = await get_main_pool()
        
        # Test basic query performance
        import time
        start_time = time.time()
        
        # This should be fast with proper indexes
        result = await pool.execute_single(
            "SELECT COUNT(*) FROM messages WHERE timestamp > datetime('now', '-1 day')"
        )
        
        query_time = time.time() - start_time
        
        print(f"Query performance test: {query_time:.3f}s")
        print(f"Recent messages: {result[0] if result else 0}")
        
        return True
        
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

async def main():
    """Main migration function."""
    print("Drongo Bot Database Migration Tool")
    print("=====================================\n")
    
    # Run migration
    success = await migrate_database()
    
    if success:
        # Verify migration
        await verify_migration()
        print("\nMigration completed successfully!")
        print("Your database is now optimized for better performance.")
    else:
        print("\nMigration failed!")
        print("Please check the logs for more information.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())