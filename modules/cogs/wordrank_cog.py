import discord
from discord.ext import commands
from discord import app_commands
import re
import aiosqlite
import os
from database_schema import get_guild_db_path

class WordRankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_word_counts(self, guild_id: int, word: str) -> dict:
        """
        Retrieves the counts of a specific word for each user in a guild.
        """
        user_counts = {}
        db_path = get_guild_db_path(str(guild_id))
        if not os.path.isfile(db_path):
            return user_counts

        query = "SELECT user_id, message_content FROM messages"
        word_pattern = re.compile(r'\b' + re.escape(word.lower()) + r'\b')
        async with aiosqlite.connect(db_path) as conn:
            async with conn.execute(query) as cursor:
                async for user_id, message_content in cursor:
                    if word_pattern.search(message_content.lower()):
                        user_counts[user_id] = user_counts.get(user_id, 0) + 1
        return user_counts

    async def format_wordrank_response(self, guild: discord.Guild, word: str, user_counts: dict) -> str:
        """
        Formats the response for the wordrank command.
        """
        if not user_counts:
            return f"No one has used the word '{word}' in this fuckin' server"
        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        response = f"Top 10 eshays who've said '{word}':\n\n"
        for i, (user_id, count) in enumerate(sorted_users, 1):
            try:
                user = await guild.fetch_member(int(user_id))
                username = user.display_name
            except discord.errors.NotFound:
                username = f"Former Member ({user_id})"
            except Exception as e:
                username = f"Unknown User ({user_id})"
                self.bot.logger.error(f"Error fetching user {user_id}: {str(e)}")
            response += f"{i}. {username}: {count} times\n"
        return response

    @app_commands.command(name="wordrank")
    @app_commands.describe(word="The word or phrase to rank users by")
    async def wordrank(self, interaction: discord.Interaction, word: str):
        """
        Ranks users in a guild based on their usage of a specific word.
        """
        await interaction.response.defer()
        try:
            user_counts = await self.get_word_counts(interaction.guild.id, word)
            response = await self.format_wordrank_response(interaction.guild, word, user_counts)
            await interaction.followup.send(response)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

async def setup(bot):
    await bot.add_cog(WordRankCog(bot))
