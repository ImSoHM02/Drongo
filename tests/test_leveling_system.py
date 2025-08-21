#!/usr/bin/env python3
"""
Test script for the leveling system implementation.
Tests XP calculation, level progression, anti-abuse systems, and core functionality.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.leveling_system import LevelingSystem
from database_pool import get_main_pool

class TestLevelingSystem:
    def __init__(self):
        # Mock bot instance
        self.bot = Mock()
        self.leveling_system = LevelingSystem(self.bot)
        self.test_guild_id = "test_guild_123456"
        self.test_user_id = "test_user_789012"
        self.test_channel_id = "test_channel_345678"
        
    async def run_all_tests(self):
        """Run all leveling system tests."""
        print("🧪 Starting Leveling System Comprehensive Tests")
        print("=" * 60)
        
        test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        # Test categories
        tests = [
            ("XP Calculation Tests", self.test_xp_calculation),
            ("Level Progression Tests", self.test_level_progression),
            ("Anti-Abuse System Tests", self.test_anti_abuse_systems),
            ("Database Integration Tests", self.test_database_integration),
            ("Configuration Tests", self.test_configuration_management),
            ("Performance Tests", self.test_performance),
            ("Error Handling Tests", self.test_error_handling)
        ]
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            print("-" * 40)
            
            try:
                result = await test_func()
                if result:
                    print(f"✅ {test_name}: PASSED")
                    test_results['passed'] += 1
                else:
                    print(f"❌ {test_name}: FAILED")
                    test_results['failed'] += 1
            except Exception as e:
                print(f"💥 {test_name}: ERROR - {str(e)}")
                test_results['failed'] += 1
                test_results['errors'].append(f"{test_name}: {str(e)}")
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print(f"✅ Passed: {test_results['passed']}")
        print(f"❌ Failed: {test_results['failed']}")
        print(f"📊 Total:  {test_results['passed'] + test_results['failed']}")
        
        if test_results['errors']:
            print("\n🚨 ERRORS:")
            for error in test_results['errors']:
                print(f"   • {error}")
        
        return test_results['failed'] == 0
    
    async def test_xp_calculation(self):
        """Test XP calculation formulas."""
        print("Testing XP calculation formulas...")
        
        # Test basic XP calculation
        test_cases = [
            ("Hello world", 5 + (0.5 * 2) + (0.1 * 11)),  # Base + words + chars
            ("A", 5 + (0.5 * 1) + (0.1 * 1)),              # Minimal message
            ("", 0),                                         # Empty message
            ("   ", 0),                                      # Whitespace only
            ("This is a very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very very long message with many words and characters to test the XP calculation formula properly and ensure it reaches the maximum cap", None)  # Max cap test - message that definitely exceeds 25 XP
        ]
        
        for message, expected_xp in test_cases:
            calculated_xp = self.leveling_system.calculate_xp(message)
            
            if expected_xp is None:  # For max cap test, just verify it hits the cap
                if calculated_xp != 25:
                    print(f"   ❌ Message: '{message}' - Expected: 25 (max cap), Got: {calculated_xp}")
                    return False
                else:
                    print(f"   ✅ Long message hits max cap: {calculated_xp} XP")
            else:
                expected_xp = min(int(expected_xp), 25)  # Apply max cap
                
                if calculated_xp != expected_xp:
                    print(f"   ❌ Message: '{message}' - Expected: {expected_xp}, Got: {calculated_xp}")
                    return False
                else:
                    print(f"   ✅ Message: '{message[:20]}...' -> {calculated_xp} XP")
        
        # Test custom configuration
        custom_config = {
            'base_xp': 10,
            'max_xp': 50,
            'word_multiplier': 1.0,
            'char_multiplier': 0.2
        }
        
        test_xp = self.leveling_system.calculate_xp("Hello world", custom_config)
        expected = min(10 + (1.0 * 2) + (0.2 * 11), 50)
        
        if test_xp != int(expected):
            print(f"   ❌ Custom config test failed - Expected: {int(expected)}, Got: {test_xp}")
            return False
        else:
            print(f"   ✅ Custom config test passed: {test_xp} XP")
        
        return True
    
    async def test_level_progression(self):
        """Test level progression calculations."""
        print("Testing level progression formulas...")
        
        # Test level calculation from XP - verify actual requirements
        # Level 1: 50*1^2 + 100*1 = 150
        # Level 2: 50*2^2 + 100*2 = 400
        # Level 3: 50*3^2 + 100*3 = 750
        # Level 4: 50*4^2 + 100*4 = 1200
        # For 10000 XP, calculate the correct level
        import math
        # 50*level^2 + 100*level = 10000
        # Using quadratic formula: level = (-100 + sqrt(10000 + 200*10000)) / 100
        level_for_10k = int((-100 + math.sqrt(10000 + 200*10000)) / 100)
        
        test_cases = [
            (0, 0),      # No XP = Level 0
            (150, 1),    # Level 1 requires 150 XP
            (400, 2),    # Level 2 requires 400 XP total
            (750, 3),    # Level 3 requires 750 XP total
            (1200, 4),   # Level 4 requires 1200 XP total
            (10000, level_for_10k)  # Higher level test - calculate actual
        ]
        
        for total_xp, expected_level in test_cases:
            calculated_level = self.leveling_system.calculate_level_from_xp(total_xp)
            
            if calculated_level != expected_level:
                print(f"   ❌ XP: {total_xp} - Expected Level: {expected_level}, Got: {calculated_level}")
                return False
            else:
                print(f"   ✅ {total_xp} XP -> Level {calculated_level}")
        
        # Test XP requirements for levels
        for level in range(1, 6):
            required_xp = self.leveling_system.get_xp_required_for_level(level)
            expected_xp = 50 * (level * level) + (100 * level)
            
            if required_xp != expected_xp:
                print(f"   ❌ Level {level} XP requirement - Expected: {expected_xp}, Got: {required_xp}")
                return False
            else:
                print(f"   ✅ Level {level} requires {required_xp} XP")
        
        # Test XP for next level calculation
        xp_needed, progress = self.leveling_system.get_xp_for_next_level(2, 100)
        level_2_xp = self.leveling_system.get_xp_required_for_level(2)
        level_3_xp = self.leveling_system.get_xp_required_for_level(3)
        expected_needed = (level_3_xp - level_2_xp) - 100
        
        if xp_needed != expected_needed:
            print(f"   ❌ Next level XP calculation failed - Expected: {expected_needed}, Got: {xp_needed}")
            return False
        else:
            print(f"   ✅ Progress calculation: {progress}% complete")
        
        return True
    
    async def test_anti_abuse_systems(self):
        """Test anti-abuse mechanisms."""
        print("Testing anti-abuse systems...")
        
        try:
            # Setup test guild config
            pool = await get_main_pool()
            await pool.execute_write("""
                INSERT OR REPLACE INTO leveling_config (guild_id, enabled, min_message_chars, min_message_words, daily_xp_cap)
                VALUES (?, ?, ?, ?, ?)
            """, (self.test_guild_id, True, 5, 2, 100))
            
            # Test message quality requirements
            test_cases = [
                ("Hi", False, "Insufficient word count"),     # Too few words
                ("A", False, "Message too short"),           # Too short
                ("Hello world", True, ""),                   # Valid message
                ("This is a good message", True, "")         # Valid message
            ]
            
            for message, should_pass, expected_reason in test_cases:
                can_earn, reason = await self.leveling_system.can_earn_xp(
                    self.test_user_id, self.test_guild_id, self.test_channel_id, message
                )
                
                if can_earn != should_pass:
                    print(f"   ❌ Message quality test failed for: '{message}'")
                    print(f"      Expected: {should_pass}, Got: {can_earn}, Reason: {reason}")
                    return False
                else:
                    status = "✅" if can_earn else "⚠️"
                    print(f"   {status} Message: '{message}' - {reason if reason else 'Valid'}")
            
            # Test channel restrictions
            await pool.execute_write("""
                UPDATE leveling_config SET blacklisted_channels = ? WHERE guild_id = ?
            """, ('["' + self.test_channel_id + '"]', self.test_guild_id))
            
            # Clear cache to reload config
            if hasattr(self.leveling_system, '_config_cache'):
                self.leveling_system._config_cache.clear()
                self.leveling_system._cache_expiry.clear()
            
            can_earn, reason = await self.leveling_system.can_earn_xp(
                self.test_user_id, self.test_guild_id, self.test_channel_id, "Hello world"
            )
            
            if can_earn:
                print(f"   ❌ Channel blacklist test failed - should be blocked")
                return False
            else:
                print(f"   ✅ Channel blacklist working: {reason}")
            
            # Reset blacklist and clear cache
            await pool.execute_write("""
                UPDATE leveling_config SET blacklisted_channels = '[]' WHERE guild_id = ?
            """, (self.test_guild_id,))
            
            # Clear cache to reload config
            if hasattr(self.leveling_system, '_config_cache'):
                self.leveling_system._config_cache.clear()
                self.leveling_system._cache_expiry.clear()
            
            return True
            
        except Exception as e:
            print(f"   ❌ Anti-abuse test error: {str(e)}")
            return False
    
    async def test_database_integration(self):
        """Test database operations."""
        print("Testing database integration...")
        
        try:
            pool = await get_main_pool()
            
            # Clean up any existing test data in proper order (dependent tables first)
            await pool.execute_write("""
                DELETE FROM xp_cooldowns WHERE user_id = ? AND guild_id = ?
            """, (self.test_user_id, self.test_guild_id))
            
            await pool.execute_write("""
                DELETE FROM xp_transactions WHERE user_id = ? AND guild_id = ?
            """, (self.test_user_id, self.test_guild_id))
            
            await pool.execute_write("""
                DELETE FROM user_levels WHERE user_id = ? AND guild_id = ?
            """, (self.test_user_id, self.test_guild_id))
            
            print("   ✅ Test data cleaned up")
            
            # Test XP awarding using the proper leveling system method
            # This method handles the correct insertion order internally
            result = await self.leveling_system.award_xp(
                self.test_user_id, self.test_guild_id, self.test_channel_id, "Hello world test message"
            )
            
            if not result['success']:
                print(f"   ❌ XP award failed: {result['reason']}")
                return False
            else:
                print(f"   ✅ XP awarded: {result['xp_awarded']} XP")
            
            # Test user data retrieval
            user_data = await self.leveling_system.get_user_level_data(self.test_user_id, self.test_guild_id)
            
            if not user_data:
                print(f"   ❌ Failed to retrieve user data")
                return False
            else:
                print(f"   ✅ User data retrieved: Level {user_data['current_level']}, {user_data['total_xp']} XP")
            
            # Test leaderboard
            leaderboard = await self.leveling_system.get_leaderboard(self.test_guild_id, 5)
            
            if len(leaderboard) == 0:
                print(f"   ❌ Leaderboard empty")
                return False
            else:
                print(f"   ✅ Leaderboard retrieved: {len(leaderboard)} entries")
            
            # Test configuration
            config = await self.leveling_system.get_guild_config(self.test_guild_id)
            
            if not config:
                print(f"   ❌ Failed to retrieve guild config")
                return False
            else:
                print(f"   ✅ Guild config retrieved: Enabled={config['enabled']}")
            
            # Verify foreign key constraints are working by checking relationships
            print("   ✅ Testing foreign key constraint integrity...")
            
            # Verify that xp_transactions reference valid user_levels
            transaction_check = await pool.execute_single("""
                SELECT COUNT(*) FROM xp_transactions xt
                LEFT JOIN user_levels ul ON xt.user_id = ul.user_id AND xt.guild_id = ul.guild_id
                WHERE xt.user_id = ? AND xt.guild_id = ? AND ul.user_id IS NULL
            """, (self.test_user_id, self.test_guild_id))
            
            if transaction_check[0] > 0:
                print(f"   ❌ Found orphaned xp_transactions records")
                return False
            else:
                print(f"   ✅ All xp_transactions have valid foreign key references")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Database test error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_configuration_management(self):
        """Test configuration management."""
        print("Testing configuration management...")
        
        try:
            # Test default config creation
            config = await self.leveling_system.get_guild_config("new_guild_test")
            
            if config['base_xp'] != 5 or config['max_xp'] != 25:
                print(f"   ❌ Default config incorrect")
                return False
            else:
                print(f"   ✅ Default config created correctly")
            
            # Test config caching
            config1 = await self.leveling_system.get_guild_config(self.test_guild_id)
            config2 = await self.leveling_system.get_guild_config(self.test_guild_id)
            
            if config1 != config2:
                print(f"   ❌ Config caching inconsistent")
                return False
            else:
                print(f"   ✅ Config caching working")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Configuration test error: {str(e)}")
            return False
    
    async def test_performance(self):
        """Test performance characteristics."""
        print("Testing performance...")
        
        try:
            import time
            
            # Test XP calculation performance
            start_time = time.time()
            for _ in range(1000):
                self.leveling_system.calculate_xp("This is a test message for performance testing")
            calc_time = time.time() - start_time
            
            if calc_time > 1.0:  # Should be very fast
                print(f"   ⚠️  XP calculation slow: {calc_time:.3f}s for 1000 calculations")
            else:
                print(f"   ✅ XP calculation performance: {calc_time:.3f}s for 1000 calculations")
            
            # Test level calculation performance
            start_time = time.time()
            for xp in range(0, 10000, 100):
                self.leveling_system.calculate_level_from_xp(xp)
            level_calc_time = time.time() - start_time
            
            if level_calc_time > 1.0:
                print(f"   ⚠️  Level calculation slow: {level_calc_time:.3f}s")
            else:
                print(f"   ✅ Level calculation performance: {level_calc_time:.3f}s")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Performance test error: {str(e)}")
            return False
    
    async def test_error_handling(self):
        """Test error handling."""
        print("Testing error handling...")
        
        try:
            # Test invalid inputs
            xp = self.leveling_system.calculate_xp(None)
            if xp != 0:
                print(f"   ❌ None input handling failed")
                return False
            else:
                print(f"   ✅ None input handled correctly")
            
            # Test negative level
            level = self.leveling_system.calculate_level_from_xp(-100)
            if level != 0:
                print(f"   ❌ Negative XP handling failed")
                return False
            else:
                print(f"   ✅ Negative XP handled correctly")
            
            # Test invalid guild ID
            config = await self.leveling_system.get_guild_config("")
            if not config or not isinstance(config, dict):
                print(f"   ❌ Invalid guild ID handling failed")
                return False
            else:
                print(f"   ✅ Invalid guild ID handled correctly")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error handling test error: {str(e)}")
            return False

async def main():
    """Main test execution."""
    tester = TestLevelingSystem()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎉 ALL TESTS PASSED! Leveling system is ready for production.")
        return 0
    else:
        print("\n💥 SOME TESTS FAILED! Please review the issues above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)