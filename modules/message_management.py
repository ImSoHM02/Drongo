# modules/message_management.py

import discord
from discord import app_commands
from database import get_db_connection
from modules.stats_display import StatsDisplay

async def delete_messages(interaction: discord.Interaction, count: int):
    # Ensure the user is authorized
    if str(interaction.user.id) != interaction.client.authorized_user_id:
        await interaction.response.send_message("only me missus can do that ay", ephemeral=True)
        return

    # Ensure count is a positive integer
    if count <= 0:
        await interaction.response.send_message("The count must be a positive integer.", ephemeral=True)
        return

    deleted_count = 0
    async for message in interaction.channel.history(limit=100):  # Adjust the limit as needed
        if message.author == interaction.client.user:
            await message.delete()
            deleted_count += 1
            if deleted_count >= count:
                break

    await interaction.response.send_message(f"Deleted {deleted_count} messages.", ephemeral=True)

async def total_messages(interaction: discord.Interaction):
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT COUNT(*) FROM messages") as cursor:
            total_count = await cursor.fetchone()
            await interaction.response.send_message(f"The total number of messages stored in the database is {total_count[0]}.")
    finally:
        await conn.close()

def setup(bot):
    @bot.tree.command(name="delete_messages")
    @app_commands.describe(count="The number of bot messages to delete")
    async def delete_messages_command(interaction: discord.Interaction, count: int):
        await delete_messages(interaction, count)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(name="total_messages")
    async def total_messages_command(interaction: discord.Interaction):
        await total_messages(interaction)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)