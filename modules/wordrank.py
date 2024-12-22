import discord
from discord import app_commands
from database import get_db_connection
import re

async def get_word_counts(guild_id: int, word: str) -> dict:
    """
    Retrieves the counts of a specific word for each user in a guild.

    Args:
        guild_id: The ID of the guild.
        word: The word to count.

    Returns:
        A dictionary where keys are user IDs and values are the word counts.
    """
    conn = await get_db_connection()
    user_counts = {}
    try:
        query = """
        SELECT user_id, message_content
        FROM messages
        WHERE guild_id = ?
        """
        word_pattern = re.compile(r'\b' + re.escape(word.lower()) + r'\b')

        async with conn.execute(query, (str(guild_id),)) as cursor:
            async for user_id, message_content in cursor:
                if word_pattern.search(message_content.lower()):
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1
    finally:
        await conn.close()
    return user_counts

async def format_wordrank_response(guild: discord.Guild, word: str, user_counts: dict) -> str:
    """
    Formats the response for the wordrank command.

    Args:
        guild: The discord guild.
        word: The word that was ranked.
        user_counts: A dictionary of user IDs and their word counts.

    Returns:
        The formatted response string.
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
            print(f"Error fetching user {user_id}: {str(e)}")

        response += f"{i}. {username}: {count} times\n"
    return response

async def wordrank(interaction: discord.Interaction, word: str):
    """
    Ranks users in a guild based on their usage of a specific word.

    Args:
        interaction: The discord interaction.
        word: The word to rank users by.
    """
    await interaction.response.defer()

    try:
        user_counts = await get_word_counts(interaction.guild.id, word)
        response = await format_wordrank_response(interaction.guild, word, user_counts)
        await interaction.followup.send(response)
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

def setup(bot):
    @bot.tree.command(name="wordrank")
    @app_commands.describe(word="The word or phrase to rank users by")
    async def wordrank_command(interaction: discord.Interaction, word: str):
        await wordrank(interaction, word)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)