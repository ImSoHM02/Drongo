# Provides classes for managing and awarding achievements.

import json
import random
import sqlite3
import asyncio
from datetime import datetime, timezone, timedelta

import discord

from database import get_db_connection
from modules.ai.anthropic.prompts import SYSTEM_PROMPT
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
        # Initialize the achievements database with enhanced schema
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main achievements table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_achievements (
                    user_id INTEGER,
                    achievement_id TEXT,
                    earned_at TIMESTAMP DEFAULT (datetime('now', 'utc')),
                    points INTEGER,
                    is_first_discoverer BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (user_id, achievement_id)
                )
            """
            )

            # Voice chat interactions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_interactions (
                    user_id INTEGER,
                    interacted_with_id INTEGER,
                    channel_id INTEGER,
                    timestamp TIMESTAMP DEFAULT (datetime('now', 'utc')),
                    PRIMARY KEY (user_id, interacted_with_id)
                )
            """
            )

            # Voice sessions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    user_id INTEGER,
                    channel_id INTEGER,
                    join_time TEXT NOT NULL,  -- Store as TEXT to preserve microsecond precision
                    PRIMARY KEY (user_id)
                )
            """
            )

            # Variable requirements tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS achievement_variables (
                    achievement_id TEXT,
                    variable_name TEXT,
                    variable_value TEXT,
                    updated_at TIMESTAMP DEFAULT (datetime('now', 'utc')),
                    expires_at TIMESTAMP,
                    PRIMARY KEY (achievement_id, variable_name)
                )
            """
            )

            # Message combo tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS message_combos (
                    user_id INTEGER,
                    combo_type TEXT,
                    start_time TIMESTAMP,
                    last_update TIMESTAMP,
                    count INTEGER DEFAULT 1,
                    PRIMARY KEY (user_id, combo_type)
                )
            """
            )

            # Add columns if they don't exist
            cursor.execute("PRAGMA table_info(user_achievements)")
            columns = [column[1] for column in cursor.fetchall()]

            if "points" not in columns:
                cursor.execute("ALTER TABLE user_achievements ADD COLUMN points INTEGER")
            if "is_first_discoverer" not in columns:
                cursor.execute("ALTER TABLE user_achievements ADD COLUMN is_first_discoverer BOOLEAN DEFAULT FALSE")

            # Initialize achievement variables
            self._initialize_achievement_variables(cursor)

            conn.commit()

    def _initialize_achievement_variables(self, cursor):
        """Initialize or update variable requirements for achievements."""
        now = datetime.now(timezone.utc)
        
        # Get current variables
        cursor.execute("SELECT achievement_id, variable_name, expires_at FROM achievement_variables")
        current_vars = {(row[0], row[1]): row[2] for row in cursor.fetchall()}

        # Update expired or missing variables
        for achievement_id, achievement in self.achievements.items():
            if achievement.variable_requirements:
                for var_name, var_config in achievement.variable_requirements.items():
                    key = (achievement_id, var_name)
                    expires_at = current_vars.get(key)

                    # Check if variable needs updating
                    if not expires_at or datetime.fromisoformat(expires_at.replace('Z', '+00:00')) <= now:
                        if var_name == 'message_count':
                            value = str(random.randint(
                                achievement.variable_requirements.get('min_count', 50),
                                achievement.variable_requirements.get('max_count', 100)
                            ))
                        elif var_name == 'time_window':
                            min_hours = achievement.variable_requirements.get('min_hours', 1)
                            max_hours = achievement.variable_requirements.get('max_hours', 24)
                            crosses_midnight = achievement.variable_requirements.get('crosses_midnight', False)
                            
                            if crosses_midnight:
                                # For time ranges that cross midnight (e.g., 23:00-04:00)
                                # Choose between the two ranges: evening or early morning
                                if random.choice([True, False]):
                                    # Evening hours
                                    value = str(random.randint(min_hours, 24))
                                else:
                                    # Early morning hours
                                    value = str(random.randint(0, max_hours))
                            else:
                                # Normal time range within the same day
                                value = str(random.randint(min_hours, max_hours))
                        elif var_name == 'number_range':
                            value = str(random.randint(
                                achievement.variable_requirements.get('min_number', 1),
                                achievement.variable_requirements.get('max_number', 100)
                            ))
                        else:
                            continue

                        # Set expiration to next day at midnight UTC
                        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                        
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO achievement_variables
                            (achievement_id, variable_name, variable_value, updated_at, expires_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (achievement_id, var_name, value, now.isoformat(), next_day.isoformat())
                        )

    async def check_achievement(
        self, message: discord.Message = None, reaction: discord.Reaction = None,
        voice_state: discord.VoiceState = None, member: discord.Member = None
    ) -> bool:
        """Check if any achievements have been triggered with enhanced mechanics."""
        achievements_earned = False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now(timezone.utc)
            
            # Update achievement variables if needed
            self._initialize_achievement_variables(cursor)
            
            # Get current variable values
            cursor.execute(
                """
                SELECT achievement_id, variable_name, variable_value
                FROM achievement_variables
                WHERE expires_at > ?
                """,
                (now.isoformat(),)
            )
            current_vars = {(row[0], row[1]): row[2] for row in cursor.fetchall()}
            
            # Check for time-based achievements
            current_hour = now.hour
            for achievement_id, achievement in self.achievements.items():
                if achievement.variable_requirements and 'time_window' in achievement.variable_requirements:
                    var_key = (achievement_id, 'time_window')
                    if var_key in current_vars:
                        required_hour = int(current_vars[var_key])
                        if current_hour == required_hour:
                            # Time-based achievement condition met
                            if message and not self.has_achievement(message.author.id, achievement_id):
                                await self.award_achievement(message.author.id, achievement_id, message.channel, achievement)
                                achievements_earned = True

        # Handle voice state updates
        if voice_state is not None and member is not None:
            # Handle voice session tracking for Marathon Speaker achievement
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if voice_state.channel is not None:  # User joined a channel
                    # Check if they already have an active session
                    cursor.execute(
                        """
                        SELECT join_time 
                        FROM voice_sessions 
                        WHERE user_id = ?
                        """,
                        (member.id,)
                    )
                    existing_session = cursor.fetchone()
                    
                    if not existing_session:
                        # Only create new session if they don't have one
                        print(f"Debug: Recording new voice join time for {member.name} in channel {voice_state.channel.name}")
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO voice_sessions 
                            (user_id, channel_id, join_time) 
                            VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%f', 'now'))
                            """,
                            (member.id, voice_state.channel.id)
                        )
                    else:
                        print(f"Debug: Preserving existing voice session for {member.name}")
                else:  # User left a channel
                    # Check if they were in a session and calculate duration
                    cursor.execute(
                        """
                        SELECT join_time 
                        FROM voice_sessions 
                        WHERE user_id = ?
                        """,
                        (member.id,)
                    )
                    result = cursor.fetchone()
                    if result:
                        # Parse join_time from UTC timestamp
                        join_time = datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                        join_time = join_time.astimezone(timezone.utc)
                        
                        # Get current time in UTC
                        current_time = datetime.now(timezone.utc)
                        print(f"Debug: Timestamps - Join: {join_time.isoformat()}, Current: {current_time.isoformat()}")
                        print(f"Debug: Voice session for {member.name} - Join time: {join_time}, Current time: {current_time}")
                        duration = current_time - join_time
                        duration_seconds = duration.total_seconds()
                        print(f"Debug: Voice session duration for {member.name}: {duration_seconds} seconds (needs 7200 seconds/2 hours)")
                        
                        # If they were in the channel for 2 hours or more
                        if duration_seconds >= 7200:  # 2 hours = 7200 seconds
                            achievement = self.achievements["MARATHON_SPEAKER"]
                            # Use the channel they were in when they left
                            try:
                                channel = voice_state.channel if voice_state.channel else member.guild.get_channel(cursor.execute(
                                    "SELECT channel_id FROM voice_sessions WHERE user_id = ?",
                                    (member.id,)
                                ).fetchone()[0])
                                
                                if channel is None:
                                    print(f"Error: Could not find channel for voice achievement for user {member.name}")
                                    channel = member.guild.text_channels[0]  # Fallback to first text channel
                                
                                print(f"Debug: Awarding MARATHON_SPEAKER to {member.name} after {duration.total_seconds()} seconds in voice")
                                await self.award_achievement(
                                    member.id, 
                                    achievement.id, 
                                    channel,
                                    achievement
                                )
                            except Exception as e:
                                print(f"Error awarding voice achievement: {e}")
                        
                        # Only clear their session if they're actually disconnecting (not switching channels)
                        if voice_state.channel is None:  # They're fully disconnecting
                            print(f"Debug: Clearing voice session for {member.name} - disconnected from voice")
                            cursor.execute(
                                "DELETE FROM voice_sessions WHERE user_id = ?",
                                (member.id,)
                            )
                        else:
                            print(f"Debug: Preserving voice session for {member.name} - switching channels")
                conn.commit()

            # Handle Social Butterfly achievement tracking
            if voice_state.channel is not None:
                # Get other members in the voice channel
                channel_members = voice_state.channel.members
                if len(channel_members) > 1:  # Only track if there are other members
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        # Record interactions with other members
                        for other_member in channel_members:
                            if other_member.id != member.id and not other_member.bot:
                                cursor.execute(
                                    """
                                    INSERT OR REPLACE INTO voice_interactions 
                                    (user_id, interacted_with_id, channel_id) 
                                    VALUES (?, ?, ?)
                                    """,
                                    (member.id, other_member.id, voice_state.channel.id)
                                )
                        conn.commit()

                        # Check if user has interacted with enough unique members
                        cursor.execute(
                            """
                            SELECT COUNT(DISTINCT interacted_with_id) 
                            FROM voice_interactions 
                            WHERE user_id = ?
                            """,
                            (member.id,)
                        )
                        unique_interactions = cursor.fetchone()[0]

                        if unique_interactions >= 3:
                            achievement = self.achievements["SOCIAL_BUTTERFLY"]
                            if await self.award_achievement(
                                member.id, achievement.id, voice_state.channel, achievement
                            ):
                                achievements_earned = True

        # Handle message achievements
        if message is not None:
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

            # Check for message patterns
            if message.content:
                # Connect to chat_history.db for message history
                for attempt in range(3):  # Try up to 3 times
                    try:
                        chat_db = await get_db_connection()
                        await chat_db.execute("BEGIN TRANSACTION")
                        
                        # Get recent messages count
                        async with chat_db.execute(
                            """
                            SELECT COUNT(*) FROM messages
                            WHERE user_id = ?
                            AND timestamp >= datetime('now', '-5 minutes')
                            ORDER BY timestamp DESC
                            LIMIT 5
                            """,
                            (str(message.author.id),)
                        ) as cursor:
                            recent_messages = (await cursor.fetchone())[0]
                        
                        if recent_messages >= 5:
                            # Get message contents
                            async with chat_db.execute(
                                """
                                SELECT message_content FROM messages
                                WHERE user_id = ?
                                AND timestamp >= datetime('now', '-5 minutes')
                                ORDER BY timestamp DESC
                                LIMIT 5
                                """,
                                (str(message.author.id),)
                            ) as cursor:
                                messages = []
                                async for row in cursor:
                                    # Extract just the message content without attachments/embeds
                                    raw_content = row[0].split('http')[0].strip()
                                    # If content is duplicated (e.g. "hi hi"), take just the first part
                                    if raw_content:
                                        words = raw_content.split()
                                        half_len = len(words) // 2
                                        if (half_len > 0 and
                                            words[:half_len] == words[half_len:]):  # Check if second half is duplicate
                                            content = ' '.join(words[:half_len])
                                        else:
                                            content = raw_content
                                        if content:  # Only add non-empty messages
                                            messages.append(content)
                                
                                if len(messages) >= 5:
                                    # Check for alternating pattern
                                    is_pattern = True
                                    for i in range(4):  # Check 4 pairs in 5 messages
                                        curr_len = len(messages[i])
                                        next_len = len(messages[i + 1])
                                        
                                        # First message should be short, second long
                                        if i % 2 == 0:
                                            if not (curr_len < 10 and next_len > 20):
                                                print(f"Pattern break: {messages[i]} ({curr_len}) -> {messages[i+1]} ({next_len})")
                                                is_pattern = False
                                                break
                                        # First message should be long, second short
                                        else:
                                            if not (curr_len > 20 and next_len < 10):
                                                print(f"Pattern break: {messages[i]} ({curr_len}) -> {messages[i+1]} ({next_len})")
                                                is_pattern = False
                                                break
                                
                                if is_pattern:
                                    achievement = self.achievements["PATTERN_MASTER"]
                                    if not self.has_achievement(message.author.id, achievement.id):
                                        await self.award_achievement(
                                            message.author.id,
                                            achievement.id,
                                            message.channel,
                                            achievement
                                        )
                        await chat_db.commit()
                        break  # Success, exit retry loop
                    except sqlite3.OperationalError as e:
                        if "database is locked" in str(e):
                            print(f"Database locked, attempt {attempt + 1}/3")
                            await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
                            if attempt == 2:  # Last attempt failed
                                print("All attempts failed due to database lock")
                                await chat_db.rollback()
                        else:
                            print(f"Database error: {e}")
                            await chat_db.rollback()
                            break
                    except Exception as e:
                        print(f"Unexpected error: {e}")
                        await chat_db.rollback()
                        break
                    finally:
                        await chat_db.close()

            if self._is_pangram(message.content):
                achievement = self.achievements["ALPHABET_SOUP"]
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
        """Award an achievement with enhanced mechanics for first discoverer and hidden achievements."""
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
                # Check if this is the first discovery
                cursor.execute(
                    "SELECT COUNT(*) FROM user_achievements WHERE achievement_id = ?",
                    (achievement_id,)
                )
                is_first = cursor.fetchone()[0] == 0
                
                # Calculate points including first discoverer bonus if applicable
                points = achievement.calculate_points(is_first)
                
                cursor.execute(
                    """
                    INSERT INTO user_achievements
                    (user_id, achievement_id, points, is_first_discoverer)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, achievement_id, points, is_first)
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
                            system=SYSTEM_PROMPT,
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

                # Create embed for achievement notification with enhanced display
                embed = discord.Embed(
                    title="🏆 Achievement Unlocked!",
                    description=ai_response,
                    color=discord.Color.gold()
                )
                
                # Show achievement name and points, including first discoverer bonus if applicable
                points_text = f"+{achievement.points:,} points"
                cursor.execute(
                    "SELECT is_first_discoverer FROM user_achievements WHERE user_id = ? AND achievement_id = ?",
                    (user_id, achievement_id)
                )
                is_first = cursor.fetchone()[0]
                if is_first and achievement.first_discoverer_bonus > 0:
                    points_text += f" (+{achievement.first_discoverer_bonus:,} First Discoverer Bonus! 🥇)"
                
                # Add achievement details with description
                embed.add_field(
                    name=achievement.name,
                    value=f"{points_text}",
                    inline=False
                )
                
                # Show progress, excluding hidden unearned achievements from total
                visible_total = sum(1 for a in self.achievements.values() if not a.hidden or self.has_achievement(user_id, a.id))
                embed.add_field(
                    name="Progress",
                    value=f"Achievements: {len(earned_achievements)}/{visible_total}\nTotal Points: {total_points:,}\nRank: #{user_rank}",
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
