# Provides classes for managing and awarding achievements.

import json
import sqlite3

import discord

from database import get_db_connection
from modules.ai.anthropic.ai_prompt import DEFAULT_SYSTEM_PROMPT
from modules.achievements.achievement_definitions import achievements

from modules.achievements.models import Achievement

class AchievementSystem:
    # Handles the logic for awarding and tracking achievements.

    def __init__(self, bot: discord.Client, config_path="modules/achievements/config.json"):
        self.bot = bot
        self.config_path = config_path
        self.config = self.load_config()
        self.db_path = self.config.get("db_path", "achievements.db")
        self.achievements = achievements

        self.setup_database()
        
    def _is_pangram(self, text: str) -> bool:
        # Check if the text contains every letter of the alphabet
        letters = set(char.lower() for char in text if char.isalpha())
        return len(letters) == 26

    def load_config(self):
        # Load the configuration from the config file.
        with open(self.config_path, "r") as f:
            return json.load(f)

    def setup_database(self):
        # Initialize the achievements database.
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER,
                    achievement_id TEXT,
                    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    points INTEGER,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """
            )

            cursor.execute("PRAGMA table_info(user_achievements)")
            columns = [column[1] for column in cursor.fetchall()]

            if "points" not in columns:
                cursor.execute("ALTER TABLE user_achievements ADD COLUMN points INTEGER")
                for achievement_id, achievement in self.achievements.items():
                    cursor.execute(
                        "UPDATE user_achievements SET points = ? WHERE achievement_id = ?",
                        (achievement.points, achievement_id),
                    )

            conn.commit()

    async def check_achievement(
        self, message: discord.Message, reaction: discord.Reaction = None
    ) -> bool:
        # Check if a message or reaction triggers any achievements.
        achievements_earned = False

        if message.content.lower() == "iwantanachievement":
            achievement = self.achievements["FIRST_REQUEST"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        has_sent_50_messages, has_sent_100_messages = await self.check_daily_message_count(
            message.author.id
        )

        if has_sent_50_messages:
            achievement = self.achievements["CHATTY"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        if has_sent_100_messages:
            achievement = self.achievements["SUPER_CHATTY"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        if message.mentions and "i love you" in message.content.lower():
            achievement = self.achievements["LOVE_HOMIES"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        if reaction:
            emoji_name = str(reaction.emoji)

            if emoji_name in ["🛍️", "👝"]:
                achievement = self.achievements["BUMBAG"]
                if await self.award_achievement(
                    reaction.member.id,
                    achievement.id,
                    reaction.message.channel,
                    achievement,
                ):
                    achievements_earned = True

            if emoji_name == "🚬":
                achievement = self.achievements["BIG_PUFF"]
                if await self.award_achievement(
                    reaction.member.id,
                    achievement.id,
                    reaction.message.channel,
                    achievement,
                ):
                    achievements_earned = True

            if emoji_name in ["👟", "🏃"]:
                achievement = self.achievements["TN_ROLL"]
                if await self.award_achievement(
                    reaction.member.id,
                    achievement.id,
                    reaction.message.channel,
                    achievement,
                ):
                    achievements_earned = True

        if "not a programmer" in message.content.lower():
            achievement = self.achievements["NOT_A_PROGRAMMER"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        if "cunt" in message.content.lower():
            achievement = self.achievements["TRUE_AUSSIE"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        if "broke your leg" in message.content.lower():
            achievement = self.achievements["BROKE_LEG"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        if "cursed_f" in message.content.lower():
            achievement = self.achievements["CURSED"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        if self._is_pangram(message.content):
            achievement = self.achievements["ALPHABET_SOUP"]
            if await self.award_achievement(
                message.author.id, achievement.id, message.channel, achievement
            ):
                achievements_earned = True

        return achievements_earned

    async def check_daily_message_count(self, user_id: str) -> tuple[bool, bool]:
        # Check if a user has sent 50 or 100 messages in the last 24 hours.
        conn = await get_db_connection()
        try:
            async with conn.execute(
                """
                SELECT COUNT(*) FROM messages 
                WHERE user_id = ? 
                AND datetime(timestamp) >= datetime('now', '-1 day')
            """,
                (str(user_id),),
            ) as cursor:
                count = (await cursor.fetchone())[0]
                has_sent_50_messages = count >= 50
                has_sent_100_messages = count >= 100
                return has_sent_50_messages, has_sent_100_messages
        finally:
            await conn.close()

    async def award_achievement(
        self, user_id: int, achievement_id: str, channel: discord.TextChannel, achievement: Achievement
    ) -> bool:
        # Award an achievement to a user if they haven't already earned it.
        guild = channel.guild
        user = guild.get_member(user_id)
        if not user:
            user = self.bot.get_user(user_id)
            if not user:
                print(f"Error: User with ID {user_id} not found.")
                return False

        if user.bot:
            return False

        if self.has_achievement(user_id, achievement_id):
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO user_achievements (user_id, achievement_id, points) VALUES (?, ?, ?)",
                    (user_id, achievement_id, achievement.points),
                )
                conn.commit()
            except sqlite3.Error as e:
                print(f"Error awarding achievement: {e}")
                return False

        # Send achievement notification
        try:
            async with channel.typing():
                # Generate AI response
                ai_response = f"Ayy {user.name} just unlocked an achievement!"
                if hasattr(self.bot, 'ai_handler') and self.bot.ai_handler:
                    try:
                        response = await self.bot.ai_handler.anthropic_client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=8192,
                            system=DEFAULT_SYSTEM_PROMPT,
                            messages=[
                                {
                                    "role": "user",
                                    "content": f"""Oi, {user.name} just earned an achievement! Give a brief, excited eshay-style response announcing their achievement. Keep it under 2 sentences and I'll format it with the achievement details after.""",
                                }
                            ],
                            temperature=0.7,
                        )
                        if response and hasattr(response, 'content') and response.content:
                            ai_response = response.content[0].text
                    except Exception as e:
                        print(f"Error generating AI response: {e}")

                try:
                    # Get user's achievements and total count
                    earned_achievements, total_possible = self.get_user_achievements(user_id)
                    
                    # Get user's rank and total points from leaderboard
                    leaderboard = await self.get_leaderboard(guild)
                    
                    # Default values if user not in leaderboard
                    user_rank = len(leaderboard) + 1 if leaderboard else 1  # If no leaderboard, they're first!
                    total_points = achievement.points  # Start with current achievement points
                    
                    # Calculate rank and total points if user exists in leaderboard
                    for i, (member, points, _) in enumerate(leaderboard or []):
                        if member.id == user_id:
                            user_rank = i + 1
                            total_points = points + achievement.points
                            break
                except Exception as e:
                    print(f"Error getting achievement stats: {e}")
                    # Use fallback values if stats calculation fails
                    earned_achievements = []
                    total_possible = len(self.achievements)
                    user_rank = 1
                    total_points = achievement.points

                # Create embed for achievement notification
                embed = discord.Embed(
                    title="🏆 Achievement Unlocked!",
                    description=ai_response,
                    color=discord.Color.gold()
                )
                embed.add_field(name=achievement.name, value=f"+{achievement.points:,} points", inline=False)
                embed.add_field(
                    name="Progress", 
                    value=f"Achievements: {len(earned_achievements)}/{total_possible}\nTotal Points: {total_points:,}\nRank: #{user_rank}", 
                    inline=False
                )
                
                # Send in channel with mention
                await channel.send(user.mention, embed=embed)
        except Exception as e:
            print(f"Error sending achievement notification: {e}")
            # Try to send a simple notification as fallback
            try:
                await channel.send(f"{user.mention} 🏆 Achievement Unlocked: **{achievement.name}** (+{achievement.points:,} points)")
            except Exception as e:
                print(f"Error sending fallback notification: {e}")
                return False

        return True

    def has_achievement(self, user_id: int, achievement_id: str) -> bool:
        # Check if a user already has a specific achievement.
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
                (user_id, achievement_id),
            )
            return cursor.fetchone() is not None

    def clear_user_achievements(self, user_id: int) -> None:
        # Clear all achievements for a specific user.
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_achievements WHERE user_id = ?", (user_id,))
            conn.commit()

    def get_user_achievements(self, user_id: int) -> tuple[list[Achievement], int]:
        # Get a user's earned achievements and total possible achievements count.
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT achievement_id FROM user_achievements WHERE user_id = ?",
                (user_id,),
            )
            earned_ids = {row[0] for row in cursor.fetchall()}

            earned_achievements = [
                achievement
                for id, achievement in self.achievements.items()
                if id in earned_ids
            ]

            total_achievements = len(self.achievements)

            return earned_achievements, total_achievements

    async def get_leaderboard(self, guild: discord.Guild) -> list[tuple[discord.Member, int, int]]:
        # Get the achievement leaderboard for a guild.
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT user_id, SUM(points) as total_points, COUNT(*) as achievement_count
                FROM user_achievements
                GROUP BY user_id
                ORDER BY total_points DESC
            """
            )
            leaderboard_data = cursor.fetchall()

        leaderboard = []
        for user_id, points, count in leaderboard_data:
            member = guild.get_member(user_id)
            if member:
                leaderboard.append((member, points, count))
        
        return leaderboard
