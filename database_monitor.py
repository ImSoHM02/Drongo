#!/usr/bin/env python3
"""
Database performance monitoring script for Drongo bot.
"""

import asyncio
import time
import logging
from datetime import datetime
from database_pool import get_main_pool
from database_utils import optimized_db

async def benchmark_queries():
    """Benchmark common database operations."""
    pool = await get_main_pool()
    
    print("Running database benchmarks...")
    
    benchmarks = []
    
    # Test 1: Simple count query
    start_time = time.time()
    result = await pool.execute_single("SELECT COUNT(*) FROM messages")
    duration = time.time() - start_time
    benchmarks.append(("Message count query", duration, result[0] if result else 0))
    
    # Test 2: User activity query
    start_time = time.time()
    result = await pool.execute_single(
        "SELECT COUNT(DISTINCT user_id) FROM messages WHERE timestamp > datetime('now', '-7 days')"
    )
    duration = time.time() - start_time
    benchmarks.append(("Active users (7 days)", duration, result[0] if result else 0))
    
    # Test 3: Complex aggregation
    start_time = time.time()
    results = await pool.execute_query(
        """
        SELECT user_id, COUNT(*) as msg_count 
        FROM messages 
        WHERE timestamp > datetime('now', '-30 days')
        GROUP BY user_id 
        ORDER BY msg_count DESC 
        LIMIT 10
        """
    )
    duration = time.time() - start_time
    benchmarks.append(("Top users (30 days)", duration, len(results)))
    
    # Display results
    print("\nBenchmark Results:")
    print("=" * 50)
    for name, duration, count in benchmarks:
        status = "[OK]" if duration < 1.0 else "[SLOW]" if duration < 5.0 else "[FAIL]"
        print(f"{status} {name:<25} {duration:.3f}s (count: {count})")
    
    return benchmarks

async def analyze_database_usage():
    """Analyze database usage patterns."""
    print("\nAnalyzing database usage...")
    
    health = await optimized_db.analyze_database_health()
    
    print(f"Database size: {health['database_size_mb']} MB")
    print(f"Tables: {', '.join(health['tables'])}")
    print(f"Indexes: {len(health['indexes'])} custom indexes")
    
    # Check for potential issues
    if health['database_size_mb'] > 1000:  # 1GB
        print("Large database size detected - consider cleanup")
    
    if health['index_count'] < 5:
        print("Few indexes detected - performance may be suboptimal")
    
    return health

async def check_connection_pool_health():
    """Check connection pool status."""
    print("\nConnection Pool Health:")
    
    pool = await get_main_pool()
    
    # Test multiple concurrent connections
    tasks = []
    for i in range(5):
        task = asyncio.create_task(test_connection_usage(pool, i))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful
    
    print(f"Successful connections: {successful}")
    if failed > 0:
        print(f"Failed connections: {failed}")
    
    return successful, failed

async def test_connection_usage(pool, connection_id):
    """Test individual connection usage."""
    try:
        async with pool.get_connection() as conn:
            await asyncio.sleep(0.1)  # Simulate work
            result = await conn.execute("SELECT 1")
            return f"Connection {connection_id} OK"
    except Exception as e:
        raise Exception(f"Connection {connection_id} failed: {e}")

async def main():
    """Main monitoring function."""
    print("Drongo Database Performance Monitor")
    print("====================================")
    
    try:
        # Run benchmarks
        benchmarks = await benchmark_queries()
        
        # Analyze usage
        await analyze_database_usage()
        
        # Check connection pool
        await check_connection_pool_health()
        
        # Overall health assessment
        print("\nOverall Health Assessment:")
        
        slow_queries = sum(1 for _, duration, _ in benchmarks if duration > 1.0)
        if slow_queries == 0:
            print("All queries performing well")
        elif slow_queries <= len(benchmarks) // 2:
            print("Some queries are slow - consider optimization")
        else:
            print("Many slow queries detected - immediate attention needed")
        
        print(f"\nReport generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"Monitoring failed: {e}")
        logging.error(f"Monitor error: {e}", exc_info=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())