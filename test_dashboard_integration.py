#!/usr/bin/env python3
"""
Simple test script to verify dashboard leveling API integration works with real data.
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "http://localhost:5001"

async def test_api_endpoint(session, endpoint, method='GET', data=None):
    """Test an API endpoint and return the response."""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method == 'GET':
            async with session.get(url) as response:
                result = await response.json()
                return response.status, result
        elif method == 'POST':
            headers = {'Content-Type': 'application/json'}
            async with session.post(url, headers=headers, json=data) as response:
                result = await response.json()
                return response.status, result
                
    except Exception as e:
        return None, {"error": str(e)}

async def test_leveling_dashboard_integration():
    """Test all leveling dashboard API endpoints."""
    
    print("🧪 Testing Leveling Dashboard API Integration")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Get available guilds
        print("\n1. Testing /api/leveling/guilds")
        status, result = await test_api_endpoint(session, "/api/leveling/guilds")
        if status == 200:
            print(f"✅ Guilds endpoint working. Found {len(result)} guilds.")
            guilds = result
        else:
            print(f"❌ Guilds endpoint failed: {status} - {result}")
            guilds = []
        
        # Use first available guild for testing, or a test guild ID
        test_guild_id = guilds[0]['id'] if guilds else "123456789012345678"
        print(f"📍 Using guild ID: {test_guild_id}")
        
        # Test 2: Get leveling stats
        print("\n2. Testing /api/leveling/stats")
        status, result = await test_api_endpoint(session, f"/api/leveling/stats?guild_id={test_guild_id}")
        if status == 200:
            print(f"✅ Stats endpoint working. Stats: {result}")
        else:
            print(f"❌ Stats endpoint failed: {status} - {result}")
        
        # Test 3: Get live feed
        print("\n3. Testing /api/leveling/live-feed")
        status, result = await test_api_endpoint(session, f"/api/leveling/live-feed?guild_id={test_guild_id}&limit=5")
        if status == 200:
            print(f"✅ Live feed endpoint working. Found {len(result)} transactions.")
            for tx in result[:3]:  # Show first 3
                print(f"   - User {tx['user_id'][-4:]}: +{tx['xp_awarded']} XP")
        else:
            print(f"❌ Live feed endpoint failed: {status} - {result}")
        
        # Test 4: Get leaderboard
        print("\n4. Testing /api/leveling/leaderboard")
        status, result = await test_api_endpoint(session, f"/api/leveling/leaderboard?guild_id={test_guild_id}&limit=5")
        if status == 200:
            print(f"✅ Leaderboard endpoint working. Found {len(result)} users.")
            for i, user in enumerate(result[:3]):  # Show top 3
                print(f"   #{i+1}: User {user['user_id'][-4:]} - Level {user['current_level']} ({user['total_xp']} XP)")
        else:
            print(f"❌ Leaderboard endpoint failed: {status} - {result}")
        
        # Test 5: Get guild configuration
        print("\n5. Testing /api/leveling/config")
        status, result = await test_api_endpoint(session, f"/api/leveling/config?guild_id={test_guild_id}")
        if status == 200:
            print(f"✅ Config endpoint working. Enabled: {result.get('enabled', 'Unknown')}")
            print(f"   - Base XP: {result.get('base_xp', 'Unknown')}")
            print(f"   - Max XP: {result.get('max_xp', 'Unknown')}")
            print(f"   - Daily Cap: {result.get('daily_xp_cap', 'Unknown')}")
        else:
            print(f"❌ Config endpoint failed: {status} - {result}")
        
        # Test 6: Get ranks
        print("\n6. Testing /api/leveling/ranks")
        status, result = await test_api_endpoint(session, f"/api/leveling/ranks?guild_id={test_guild_id}")
        if status == 200:
            print(f"✅ Ranks endpoint working. Found {len(result)} ranks.")
        else:
            print(f"❌ Ranks endpoint failed: {status} - {result}")
        
        # Test 7: Get rewards
        print("\n7. Testing /api/leveling/rewards")
        status, result = await test_api_endpoint(session, f"/api/leveling/rewards?guild_id={test_guild_id}")
        if status == 200:
            print(f"✅ Rewards endpoint working. Found {len(result)} rewards.")
        else:
            print(f"❌ Rewards endpoint failed: {status} - {result}")
        
        # Test 8: Test user stats (if we have users from leaderboard)
        print("\n8. Testing /api/leveling/user-stats")
        if 'result' in locals() and isinstance(result, list) and len(result) > 0:
            test_user_id = result[0]['user_id']
            status, user_result = await test_api_endpoint(session, f"/api/leveling/user-stats?user_id={test_user_id}&guild_id={test_guild_id}")
            if status == 200:
                print(f"✅ User stats endpoint working for user {test_user_id[-4:]}.")
                print(f"   - Level: {user_result.get('current_level', 'Unknown')}")
                print(f"   - XP: {user_result.get('total_xp', 'Unknown')}")
                print(f"   - Messages: {user_result.get('messages_sent', 'Unknown')}")
            else:
                print(f"❌ User stats endpoint failed: {status} - {user_result}")
        else:
            print("⚠️  Skipping user stats test (no users found)")
    
    print("\n" + "=" * 50)
    print("🎉 Integration Test Complete!")
    print("\nNext steps:")
    print("1. Start the dashboard server: python web/dashboard_server.py")
    print("2. Visit http://localhost:5001/dashboard/leveling")
    print("3. Select a guild and explore the live data!")

if __name__ == "__main__":
    asyncio.run(test_leveling_dashboard_integration())