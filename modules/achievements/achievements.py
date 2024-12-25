import sqlite3
import discord
from modules.ai.anthropic.ai_prompt import DEFAULT_SYSTEM_PROMPT

class AchievementSystem:
    def __init__(self, bot: discord.Client, db_path='achievements.db'):
        self.bot = bot
        self.db_path = db_path
        self.setup_database()

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
            return await self.award_achievement(
                message.author.id,
                "FIRST_REQUEST",
                message.channel,
                "Ay brah, you just earned your first achievement by askin' for one!"
            )
        return False

    async def award_achievement(self, user_id: int, achievement_id: str, channel: discord.TextChannel, context: str) -> bool:
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
                model="claude-3-opus-20240229",
                max_tokens=100,
                system=DEFAULT_SYSTEM_PROMPT,
                messages=[{
                    "role": "user", 
                    "content": f"""Oi, this legend just earned an achievement! Here's what happened:
{context}

Give a brief, excited eshay-style response announcing their achievement. Keep it under 2 sentences."""
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
