import sqlite3
import discord
from modules.ai.anthropic.ai_prompt import DEFAULT_SYSTEM_PROMPT

class Achievement:
    def __init__(self, id: str, name: str, description: str):
        self.id = id
        self.name = name
        self.description = description

class AchievementSystem:
    def __init__(self, bot: discord.Client, db_path='achievements.db'):
        self.bot = bot
        self.db_path = db_path
        self.setup_database()
        
        # Define achievements
        self.achievements = {
            "FIRST_REQUEST": Achievement(
                "FIRST_REQUEST",
                "Test Achievement",
                "Earned by asking for an achievement using the 'iwantanachievement' secret word"
            )
        }

    def setup_database(self):
        """Initialize the achievements database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER,
                    achievement_id TEXT,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, achievement_id)
                )
            ''')
            conn.commit()

    async def check_achievement(self, message: discord.Message) -> bool:
        """Check if a message triggers any achievements."""
        if message.content.lower() == "iwantanachievement":
            achievement = self.achievements["FIRST_REQUEST"]
            return await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            )
        return False

    async def award_achievement(self, user_id: int, achievement_id: str, channel: discord.TextChannel, achievement: Achievement) -> bool:
        """Award an achievement to a user if they haven't already earned it."""
        if self.has_achievement(user_id, achievement_id):
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)',
                (user_id, achievement_id)
            )
            conn.commit()

        # Generate AI response about the achievement
        async with channel.typing():
            response = await self.bot.ai_handler.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                system=DEFAULT_SYSTEM_PROMPT,
                messages=[{
                    "role": "user", 
                    "content": f"""Oi, this legend just earned the "{achievement.name}" achievement! Here's what it's for:
{achievement.description}

Give a brief, excited eshay-style response announcing their achievement, mentioning both the achievement name and why they got it. Keep it under 2 sentences."""
                }],
                temperature=0.7,
            )
            ai_response = response.content[0].text
            await channel.send(ai_response)
        return True

    def has_achievement(self, user_id: int, achievement_id: str) -> bool:
        """Check if a user already has a specific achievement."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?',
                (user_id, achievement_id)
            )
            return cursor.fetchone() is not None
