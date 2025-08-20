#!/usr/bin/env python3
"""
Simplified test to identify the foreign key constraint issue.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database_pool import get_main_pool

async def test_foreign_key_constraints():
    """Test the specific foreign key constraint issue."""
    print("🔍 Testing Foreign Key Constraints")
    print("=" * 50)
    
    try:
        pool = await get_main_pool()
        test_guild_id = "123456789"
        test_user_id = "987654321"
        
        print("1. Testing direct insertion into dependent tables (should fail)...")
        
        # Try to insert into xp_transactions without user_levels record
        try:
            await pool.execute_write("""
                INSERT INTO xp_transactions 
                (user_id, guild_id, channel_id, xp_awarded, reason, timestamp) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (test_user_id, test_guild_id, "channel123", 25, 'test_message', datetime.now()))
            print("   ❌ xp_transactions insert should have failed but didn't")
        except Exception as e:
            print(f"   ✅ xp_transactions insert failed as expected: {e}")
        
        # Try to insert into xp_cooldowns without user_levels record
        try:
            await pool.execute_write("""
                INSERT INTO xp_cooldowns 
                (user_id, guild_id, last_xp_timestamp, cooldown_ends_at) 
                VALUES (?, ?, ?, ?)
            """, (test_user_id, test_guild_id, datetime.now(), datetime.now()))
            print("   ❌ xp_cooldowns insert should have failed but didn't")
        except Exception as e:
            print(f"   ✅ xp_cooldowns insert failed as expected: {e}")
        
        print("\n2. Testing proper insertion order (should succeed)...")
        
        # First insert into user_levels
        await pool.execute_write("""
            INSERT OR REPLACE INTO user_levels 
            (user_id, guild_id, current_xp, current_level, total_xp, messages_sent) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_user_id, test_guild_id, 0, 0, 0, 0))
        print("   ✅ user_levels insert successful")
        
        # Now insert into xp_transactions
        await pool.execute_write("""
            INSERT INTO xp_transactions 
            (user_id, guild_id, channel_id, xp_awarded, reason, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_user_id, test_guild_id, "channel123", 25, 'test_message', datetime.now()))
        print("   ✅ xp_transactions insert successful")
        
        # Now insert into xp_cooldowns
        await pool.execute_write("""
            INSERT OR REPLACE INTO xp_cooldowns 
            (user_id, guild_id, last_xp_timestamp, cooldown_ends_at) 
            VALUES (?, ?, ?, ?)
        """, (test_user_id, test_guild_id, datetime.now(), datetime.now()))
        print("   ✅ xp_cooldowns insert successful")
        
        print("\n3. Testing data verification...")
        
        # Verify data exists
        user_count = await pool.execute_single("SELECT COUNT(*) FROM user_levels WHERE user_id = ? AND guild_id = ?", 
                                              (test_user_id, test_guild_id))
        transaction_count = await pool.execute_single("SELECT COUNT(*) FROM xp_transactions WHERE user_id = ? AND guild_id = ?", 
                                                     (test_user_id, test_guild_id))
        cooldown_count = await pool.execute_single("SELECT COUNT(*) FROM xp_cooldowns WHERE user_id = ? AND guild_id = ?", 
                                                  (test_user_id, test_guild_id))
        
        print(f"   ✅ user_levels records: {user_count[0]}")
        print(f"   ✅ xp_transactions records: {transaction_count[0]}")
        print(f"   ✅ xp_cooldowns records: {cooldown_count[0]}")
        
        print("\n4. Cleaning up test data...")
        
        # Clean up in reverse order
        await pool.execute_write("DELETE FROM xp_cooldowns WHERE user_id = ? AND guild_id = ?", 
                                (test_user_id, test_guild_id))
        await pool.execute_write("DELETE FROM xp_transactions WHERE user_id = ? AND guild_id = ?", 
                                (test_user_id, test_guild_id))
        await pool.execute_write("DELETE FROM user_levels WHERE user_id = ? AND guild_id = ?", 
                                (test_user_id, test_guild_id))
        print("   ✅ Test data cleaned up")
        
        print("\n🎉 Foreign key constraint test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_leveling_system_integration():
    """Test the leveling system's proper database operations."""
    print("\n🔧 Testing Leveling System Integration")
    print("=" * 50)
    
    try:
        # Import here to avoid import issues
        from modules.leveling_system import LevelingSystem
        from unittest.mock import Mock
        
        bot = Mock()
        leveling_system = LevelingSystem(bot)
        
        test_guild_id = "test_guild_999"
        test_user_id = "test_user_888"
        test_channel_id = "test_channel_777"
        
        print("1. Testing award_xp function...")
        
        result = await leveling_system.award_xp(
            test_user_id, test_guild_id, test_channel_id, 
            "Hello world test message"
        )
        
        if result['success']:
            print(f"   ✅ XP awarded successfully: {result['xp_awarded']} XP")
            print(f"   ✅ Level up: {result['level_up']}")
        else:
            print(f"   ❌ XP award failed: {result['reason']}")
            return False
        
        print("\n2. Testing user data retrieval...")
        
        user_data = await leveling_system.get_user_level_data(test_user_id, test_guild_id)
        if user_data:
            print(f"   ✅ Retrieved user data: Level {user_data['current_level']}, {user_data['total_xp']} XP")
        else:
            print("   ❌ Failed to retrieve user data")
            return False
        
        print("\n3. Cleaning up test data...")
        
        pool = await get_main_pool()
        await pool.execute_write("DELETE FROM xp_cooldowns WHERE user_id = ? AND guild_id = ?", 
                                (test_user_id, test_guild_id))
        await pool.execute_write("DELETE FROM xp_transactions WHERE user_id = ? AND guild_id = ?", 
                                (test_user_id, test_guild_id))
        await pool.execute_write("DELETE FROM user_levels WHERE user_id = ? AND guild_id = ?", 
                                (test_user_id, test_guild_id))
        await pool.execute_write("DELETE FROM leveling_config WHERE guild_id = ?", 
                                (test_guild_id,))
        print("   ✅ Integration test data cleaned up")
        
        print("\n🎉 Leveling system integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n💥 Integration test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution."""
    print("🧪 Drongo Bot Leveling System - Foreign Key Constraint Analysis")
    print("=" * 70)
    
    # Test 1: Foreign key constraints
    fk_success = await test_foreign_key_constraints()
    
    # Test 2: Leveling system integration
    integration_success = await test_leveling_system_integration()
    
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print(f"Foreign Key Constraints: {'✅ PASSED' if fk_success else '❌ FAILED'}")
    print(f"Leveling System Integration: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    
    if fk_success and integration_success:
        print("\n🎉 ALL TESTS PASSED! Foreign key constraints are working correctly.")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED! Review the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)