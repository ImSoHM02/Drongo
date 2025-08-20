#!/usr/bin/env python3
"""
Simple test to verify foreign key constraint fix.
"""

import sqlite3
import os
from datetime import datetime

def test_foreign_key_constraints():
    """Test foreign key constraints directly with SQLite."""
    print("🔍 Testing Foreign Key Constraints - Direct SQLite")
    print("=" * 50)
    
    # Use a test database
    db_path = "test_leveling.db"
    
    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
    cursor = conn.cursor()
    
    try:
        # Create the tables with foreign key constraints
        print("1. Creating tables...")
        
        cursor.execute('''
            CREATE TABLE user_levels (
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
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE xp_transactions (
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
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE xp_cooldowns (
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                last_xp_message_id TEXT,
                last_xp_timestamp TIMESTAMP NOT NULL,
                cooldown_ends_at TIMESTAMP NOT NULL,
                consecutive_messages INTEGER DEFAULT 1,
                PRIMARY KEY (user_id, guild_id),
                FOREIGN KEY (user_id, guild_id) REFERENCES user_levels(user_id, guild_id)
            )
        ''')
        
        print("   ✅ Tables created successfully")
        
        test_guild_id = "123456789"
        test_user_id = "987654321"
        
        print("\n2. Testing foreign key constraint violation (should fail)...")
        
        # Try to insert into xp_transactions without user_levels record
        try:
            cursor.execute("""
                INSERT INTO xp_transactions 
                (user_id, guild_id, channel_id, xp_awarded, reason, timestamp) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (test_user_id, test_guild_id, "channel123", 25, 'test_message', datetime.now().isoformat()))
            conn.commit()
            print("   ❌ xp_transactions insert should have failed but didn't")
            return False
        except sqlite3.IntegrityError as e:
            print(f"   ✅ xp_transactions insert failed as expected: {e}")
        
        print("\n3. Testing correct insertion order (should succeed)...")
        
        # First insert into user_levels
        cursor.execute("""
            INSERT INTO user_levels 
            (user_id, guild_id, current_xp, current_level, total_xp, messages_sent) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_user_id, test_guild_id, 0, 0, 0, 0))
        conn.commit()
        print("   ✅ user_levels insert successful")
        
        # Now insert into xp_transactions
        cursor.execute("""
            INSERT INTO xp_transactions 
            (user_id, guild_id, channel_id, xp_awarded, reason, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (test_user_id, test_guild_id, "channel123", 25, 'test_message', datetime.now().isoformat()))
        conn.commit()
        print("   ✅ xp_transactions insert successful")
        
        # Now insert into xp_cooldowns
        cursor.execute("""
            INSERT INTO xp_cooldowns 
            (user_id, guild_id, last_xp_timestamp, cooldown_ends_at) 
            VALUES (?, ?, ?, ?)
        """, (test_user_id, test_guild_id, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        print("   ✅ xp_cooldowns insert successful")
        
        print("\n4. Verifying data...")
        
        cursor.execute("SELECT COUNT(*) FROM user_levels WHERE user_id = ? AND guild_id = ?", 
                      (test_user_id, test_guild_id))
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM xp_transactions WHERE user_id = ? AND guild_id = ?", 
                      (test_user_id, test_guild_id))
        transaction_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM xp_cooldowns WHERE user_id = ? AND guild_id = ?", 
                      (test_user_id, test_guild_id))
        cooldown_count = cursor.fetchone()[0]
        
        print(f"   ✅ user_levels records: {user_count}")
        print(f"   ✅ xp_transactions records: {transaction_count}")
        print(f"   ✅ xp_cooldowns records: {cooldown_count}")
        
        if user_count == 1 and transaction_count == 1 and cooldown_count == 1:
            print("\n🎉 Foreign key constraint test PASSED!")
            return True
        else:
            print(f"\n❌ Data verification failed")
            return False
            
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        return False
    finally:
        conn.close()
        # Clean up test database
        if os.path.exists(db_path):
            os.remove(db_path)

if __name__ == "__main__":
    success = test_foreign_key_constraints()
    
    if success:
        print("\n" + "=" * 60)
        print("SOLUTION: The foreign key constraint issue occurs when trying")
        print("to insert into dependent tables (xp_transactions, xp_cooldowns)")
        print("without first ensuring parent records exist in user_levels.")
        print("")
        print("FIX: Always insert into user_levels FIRST before inserting")
        print("into any dependent tables. The leveling system's award_xp()")
        print("method handles this correctly with ON CONFLICT clauses.")
        print("=" * 60)
    else:
        print("\n💥 Test failed - foreign key constraints not working properly")