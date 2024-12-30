import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.achievements.achievements import AchievementSystem
import discord

# Create a mock bot instance since AchievementSystem requires it
class MockBot:
    def __init__(self):
        self.user = None

# Initialize achievement system to trigger database update
bot = MockBot()
achievement_system = AchievementSystem(bot)

# Explicitly update points for all existing achievements
import sqlite3
with sqlite3.connect('achievements.db') as conn:
    cursor = conn.cursor()
    
    # Update points for all existing achievements
    for achievement_id, achievement in achievement_system.achievements.items():
        cursor.execute(
            'UPDATE user_achievements SET points = ? WHERE achievement_id = ?',
            (achievement.points, achievement_id)
        )
    conn.commit()

print("Achievement database has been updated and points have been set for all existing achievements.")
