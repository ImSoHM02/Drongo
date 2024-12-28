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
                "Talks-a-lot",
                "Sent 50 messages in a single day"
            ),
            "SUPER_CHATTY": Achievement(
                "SUPER_CHATTY",
                "Talks-too-much",
                "Sent 100 messages in a single day"
            ),
            "LOVE_HOMIES": Achievement(
                "LOVE_HOMIES",
                "Showing some love to the homies <3",
                "We love our homies"
            ),
            "BUMBAG": Achievement(
                "BUMBAG",
                "Bumbag",
                "You adjusted your bumbag in public"
            ),
            "BIG_PUFF": Achievement(
                "BIG_PUFF",
                "Big Puff",
                "Took a big puff of your ciggie"
            ),
            "TN_ROLL": Achievement(
                "TN_ROLL",
                "Rolled your first pair of TN's",
                "Rolled a fuckin' nerd for his TN's"
            ),
            "NOT_A_PROGRAMMER": Achievement(
                "NOT_A_PROGRAMMER",
                "Not a programmer",
                "Probably sarcastically told Sean he's not a programmer"
            ),
            "TRUE_AUSSIE": Achievement(
                "TRUE_AUSSIE",
                "True Aussie",
                "Used some true Aussie insults"
            ),
            "FLUX_COMMAND": Achievement(
                "FLUX_COMMAND",
                "Is it porn?",
                "Generated an image using Fini's Flux (Probably porn)"
            ),
            "BROKE_LEG": Achievement(
                "BROKE_LEG",
                "MY LEG!",
                "Probably talking about how Jamie broke his leg"
            ),
            "CURSED": Achievement(
                "CURSED",
                "Cursed",
                "Used the best emoji of all time"
            ),
            "LOST_EVEN_ODD": Achievement(
                "LOST_EVEN_ODD",
                "Lost the even/odd",
                "Didn't have enough Lucky Rabbit Feet equipped"
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

    async def check_achievement(self, message: discord.Message, reaction: discord.Reaction = None) -> bool:
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

        # Check for chatty achievements
        has_50, has_100 = await self.check_daily_messages(message.author.id)
        
        if has_50:
            achievement = self.achievements["CHATTY"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True
                
        if has_100:
            achievement = self.achievements["SUPER_CHATTY"]
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

        # Check for reaction-based achievements if a reaction was provided
        if reaction:
            emoji_name = str(reaction.emoji)
            
            # Check for bumbag achievement
            if emoji_name in ['🛍️', '👝']:  # pouch or clutch_bag
                achievement = self.achievements["BUMBAG"]
                if await self.award_achievement(
                    reaction.member.id,
                    achievement.id,
                    reaction.message.channel,
                    achievement
                ):
                    achievements_earned = True
            
            # Check for big puff achievement
            if emoji_name == '🚬':  # smoking
                achievement = self.achievements["BIG_PUFF"]
                if await self.award_achievement(
                    reaction.member.id,
                    achievement.id,
                    reaction.message.channel,
                    achievement
                ):
                    achievements_earned = True
            
            # Check for TN roll achievement
            if emoji_name in ['👟', '🏃']:  # athletic_shoe or running_shoe
                achievement = self.achievements["TN_ROLL"]
                if await self.award_achievement(
                    reaction.member.id,
                    achievement.id,
                    reaction.message.channel,
                    achievement
                ):
                    achievements_earned = True

        # Check for "not a programmer" achievement
        if "not a programmer" in message.content.lower():
            achievement = self.achievements["NOT_A_PROGRAMMER"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        # Check for "True Aussie" achievement
        if "cunt" in message.content.lower():
            achievement = self.achievements["TRUE_AUSSIE"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        # Check for Flux command usage
        if message.content.lower().startswith('flux') or (hasattr(message, 'interaction') and message.interaction and message.interaction.command.name == 'flux'):
            achievement = self.achievements["FLUX_COMMAND"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        # Check for "broke your leg" achievement
        if "broke your leg" in message.content.lower():
            achievement = self.achievements["BROKE_LEG"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        # Check for cursed_f emoji in message
        if "cursed_f" in message.content.lower():
            achievement = self.achievements["CURSED"]
            if await self.award_achievement(
                message.author.id,
                achievement.id,
                message.channel,
                achievement
            ):
                achievements_earned = True

        # Check for lost even/odd achievement
        if message.author.id == 608114286082129921:  # Convert to integer comparison
            content = message.content.lower()
            if "your winnings" in content and "0" in content.split("your winnings")[1].split("\n")[0]:
                achievement = self.achievements["LOST_EVEN_ODD"]
                if await self.award_achievement(
                    message.author.id,
                    achievement.id,
                    message.channel,
                    achievement
                ):
                    achievements_earned = True

        return achievements_earned

    async def check_daily_messages(self, user_id: str) -> tuple[bool, bool]:
        """Check if a user has sent 50 or 100 messages in the last 24 hours.
        Returns a tuple of (has_50, has_100)"""
        conn = await get_db_connection()
        try:
            async with conn.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE user_id = ? 
                AND datetime(timestamp) >= datetime('now', '-1 day')
            """, (str(user_id),)) as cursor:
                count = (await cursor.fetchone())[0]
                return count >= 50, count >= 100
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

        # Get user mention from the guild member
        guild = channel.guild
        user = guild.get_member(user_id)
        if not user:
            # Fallback to bot.get_user if guild.get_member fails
            user = self.bot.get_user(user_id)
            if not user:
                return False

        # Generate AI response about the achievement
        async with channel.typing():
            response = await self.bot.ai_handler.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8192,
                system=DEFAULT_SYSTEM_PROMPT,
                messages=[{
                    "role": "user", 
                    "content": f"""Oi, {user.name} just earned an achievement! Give a brief, excited eshay-style response announcing their achievement. Keep it under 2 sentences and I'll format it with the achievement details after."""
                }],
                temperature=0.7,
            )
            ai_response = response.content[0].text
            
            # Format the achievement announcement with Discord markdown
            formatted_message = f"{user.mention} {ai_response}\n\n> 🏆 **{achievement.name}**\n> ```\n> {achievement.description}\n> ```"
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

    def get_user_achievements(self, user_id: int) -> tuple[list[Achievement], int]:
        """Get a user's earned achievements and total possible achievements count."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT achievement_id FROM user_achievements WHERE user_id = ?',
                (user_id,)
            )
            earned_ids = {row[0] for row in cursor.fetchall()}
            
            earned_achievements = [
                achievement for id, achievement in self.achievements.items()
                if id in earned_ids
            ]
            
            total_achievements = len(self.achievements)
            
            return earned_achievements, total_achievements
