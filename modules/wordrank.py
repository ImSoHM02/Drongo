import discord
from discord import app_commands
from database import get_db_connection
import re

async def wordrank(interaction: discord.Interaction, word: str):
    await interaction.response.defer()  # Defer the response to avoid timeout

    conn = await get_db_connection()
    try:
        query = """
        SELECT user_id, message_content
        FROM messages
        WHERE guild_id = ?
        """
        
        word_pattern = re.compile(r'\b' + re.escape(word.lower()) + r'\b')
        user_counts = {}

        async with conn.execute(query, (str(interaction.guild.id),)) as cursor:
            async for user_id, message_content in cursor:
                if word_pattern.search(message_content.lower()):
                    user_counts[user_id] = user_counts.get(user_id, 0) + 1

        if not user_counts:
            await interaction.followup.send(f"No one has used the word '{word}' in this server, ya dumb cunt")
            return

        sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        response = f"Top 10 users who've said '{word}':\n\n"
        for i, (user_id, count) in enumerate(sorted_users, 1):
            try:
                user = await interaction.guild.fetch_member(int(user_id))
                username = user.name
            except discord.errors.NotFound:
                username = f"Former Member ({user_id})"
            except Exception as e:
                username = f"Unknown User ({user_id})"
                print(f"Error fetching user {user_id}: {str(e)}")
            
            response += f"{i}. {username}: {count} times\n"

        await interaction.followup.send(response)

    except Exception as e:
        await interaction.followup.send(f"Fuuuuck cunt something ain't right ay:: {str(e)}")
    finally:
        await conn.close()

def setup(bot):
    @bot.tree.command(name="wordrank")
    @app_commands.describe(word="The word or phrase to rank users by")
    async def wordrank_command(interaction: discord.Interaction, word: str):
        await wordrank(interaction, word)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)