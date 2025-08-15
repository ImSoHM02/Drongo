import discord
import io
import re
from discord.ext import commands
from discord import app_commands
from database import get_db_connection

class WordCountCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def count_word_occurrences(self, interaction: discord.Interaction, user: discord.User, word: str) -> tuple[int, list[str]]:
        """Counts the occurrences of a word in a user's messages and returns the count and matching messages."""
        conn = await get_db_connection()
        try:
            query = "SELECT message_content FROM messages WHERE user_id = ? AND guild_id = ?"
            word_pattern = re.compile(r'(?i)(?:^|[^\w])(' + re.escape(word) + r')(?=[^\w]|$)')
            count = 0
            matching_messages = []
            async with conn.execute(query, (str(user.id), str(interaction.guild_id))) as cursor:
                async for (message_content,) in cursor:
                    matches = word_pattern.findall(message_content)
                    count += len(matches)
                    if matches:
                        matching_messages.append(message_content)
            return count, matching_messages
        finally:
            await conn.close()

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
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

async def setup(bot):
    await bot.add_cog(WordCountCog(bot))