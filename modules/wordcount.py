import discord
import io
import asyncio
import re
from discord import app_commands
from database import get_db_connection

async def count_word_occurrences(interaction: discord.Interaction, user: discord.User, word: str) -> tuple[int, list[str]]:
    """Counts the occurrences of a word in a user's messages and returns the count and matching messages."""

    if user.bot:
        return 0, []  # Ignore bots

    conn = await get_db_connection()
    try:
        query = """
        SELECT message_content
        FROM messages
        WHERE user_id = ? AND guild_id = ?
        """
        # Improved word pattern:
        # - \b: Matches word boundaries, ensuring it's a whole word.
        # - (?i): Case-insensitive flag.
        # - \W: Matches any non-word character (including whitespace and punctuation)
        word_pattern = re.compile(r'(?i)\b' + re.escape(word) + r'\b(?=\W|$)')
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

async def send_word_count_response(interaction: discord.Interaction, user: discord.User, word: str, count: int):
    """Sends the initial response with the word count."""

    response = f"{user.name} has said '{word}' {count} times in this server."
    await interaction.followup.send(response)

async def offer_message_instances(interaction: discord.Interaction, user: discord.User, word: str, matching_messages: list[str]):
    """Asks the user if they want to see the message instances and sends them if requested."""

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.content.lower() == "yes drongo"

    await interaction.followup.send("You wanna see the messages this cunt sent? Say 'yes drongo' like a good human")

    try:
        await interaction.client.wait_for('message', check=check, timeout=30.0)

        file_content = f"Instances of '{word}' used by {user.name} (up to 50 messages):\n\n"
        file_content += "\n\n".join(matching_messages[:50])

        file = io.BytesIO(file_content.encode('utf-8'))
        discord_file = discord.File(file, filename=f"{user.name}_{word}_instances.txt")

        await interaction.followup.send("Here ya go ya dog:", file=discord_file)
    except asyncio.TimeoutError:
        await interaction.followup.send("Guess you didn't wanna see the weird shit this cunt said")

async def wordcount(interaction: discord.Interaction, user: discord.User, word: str):
    """Handles the wordcount command logic."""

    if user.bot:
        await interaction.response.send_message(f"I can't count the words for {user.name} because they ain't got no soul")
        return

    await interaction.response.defer()

    count, matching_messages = await count_word_occurrences(interaction, user, word)

    await send_word_count_response(interaction, user, word, count)

    if count > 0:
        await offer_message_instances(interaction, user, word, matching_messages)

def setup(bot):
    @bot.tree.command(name="wordcount")
    @app_commands.describe(user="The user to check", word="The word or phrase to count")
    async def wordcount_command(interaction: discord.Interaction, user: discord.User, word: str):
        await wordcount(interaction, user, word)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)