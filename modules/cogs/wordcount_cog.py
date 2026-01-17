import discord
import io
import re
import aiosqlite
import os
from discord.ext import commands
from discord import app_commands
from database_modules.database_schema import get_guild_db_path

class WordCountCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def count_word_occurrences(self, interaction: discord.Interaction, user: discord.User, word: str) -> tuple[int, list[str]]:
        """Counts the occurrences of a word in a user's messages and returns the count and matching messages."""
        db_path = get_guild_db_path(str(interaction.guild_id))
        if not os.path.isfile(db_path):
            return 0, []

        query = "SELECT message_content FROM messages WHERE user_id = ?"
        word_pattern = re.compile(r'(?i)(?:^|[^\\w])(' + re.escape(word) + r')(?=[^\\w]|$)')
        count = 0
        matching_messages = []

        async with aiosqlite.connect(db_path) as conn:
            async with conn.execute(query, (str(user.id),)) as cursor:
                async for (message_content,) in cursor:
                    matches = word_pattern.findall(message_content)
                    count += len(matches)
                    if matches:
                        matching_messages.append(message_content)
        return count, matching_messages

    async def send_word_count_response(self, interaction: discord.Interaction, user: discord.User, word: str, count: int, matching_messages: list[str]):
        """Sends the response with the word count and instances."""
        response = f"{user.name} has said '{word}' {count} times in this server."
        if count > 0:
            file_content = f"Instances of '{word}' used by {user.name} (up to 50 messages):\n\n"
            file_content += "\n\n".join(matching_messages[:50])
            file = io.BytesIO(file_content.encode('utf-8'))
            discord_file = discord.File(file, filename=f"{user.name}_{word}_instances.txt")
            await interaction.followup.send(response, file=discord_file)
        else:
            await interaction.followup.send(response)

    @app_commands.command(name="wordcount")
    @app_commands.describe(user="The user to check", word="The word or phrase to count")
    async def wordcount(self, interaction: discord.Interaction, user: discord.User, word: str):
        """Counts how many times a user has said a specific word."""
        await interaction.response.defer()
        count, matching_messages = await self.count_word_occurrences(interaction, user, word)
        await self.send_word_count_response(interaction, user, word, count, matching_messages)
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

async def setup(bot):
    await bot.add_cog(WordCountCog(bot))
