import sqlite3
import discord
from modules.ai.anthropic.ai_prompt import DEFAULT_SYSTEM_PROMPT
from database import get_db_connection

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
            ),
            "CHATTY": Achievement(
                "CHATTY",
                "Chatterbox",
                "Sent 50 messages in a single day"
            ),
            "LOVE_HOMIES": Achievement(
                "LOVE_HOMIES",
                "Showing some love to the homies <3",
                "We love our homies"
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
        achievements_earned = False

        # Check for the test achievement
        if message.content.lower() == "iwantanachievement":
            achievement = self.achievements["FIRST_REQUEST"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        # Check for chatty achievement
        if await self.check_daily_messages(message.author.id):
            achievement = self.achievements["CHATTY"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        # Check for love homies achievement
        if message.mentions and "i love you" in message.content.lower():
            achievement = self.achievements["LOVE_HOMIES"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        return achievements_earned

    async def check_daily_messages(self, user_id: str) -> bool:
        """Check if a user has sent 50 messages in the last 24 hours."""
        conn = await get_db_connection()
        try:
            async with conn.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE user_id = ? 
                AND datetime(timestamp) >= datetime('now', '-1 day')
            """, (str(user_id),)) as cursor:
                count = (await cursor.fetchone())[0]
                return count >= 50
        finally:
            await conn.close()

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
                    "content": f"""Oi, this legend just earned an achievement! Give a brief, excited eshay-style response announcing their achievement. Keep it under 2 sentences and I'll format it with the achievement details after."""
                }],
                temperature=0.7,
            )
            ai_response = response.content[0].text
            
            # Format the achievement announcement with Discord markdown
            formatted_message = f"{ai_response}\n\n> 🏆 **{achievement.name}**\n> ```\n> {achievement.description}\n> ```"
            await channel.send(formatted_message)
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
