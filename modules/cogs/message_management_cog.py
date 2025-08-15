import discord
from discord.ext import commands
from discord import app_commands
from database import get_db_connection

class MessageManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="delete_messages")
    @app_commands.describe(count="The number of bot messages to delete")
    async def delete_messages(self, interaction: discord.Interaction, count: int):
        """Deletes a specified number of the bot's messages from the channel."""
        if str(interaction.user.id) != self.bot.authorized_user_id:
            await interaction.response.send_message("only me missus can do that ay", ephemeral=True)
            return

        if count <= 0:
            await interaction.response.send_message("The count must be a positive integer.", ephemeral=True)
            return

        deleted_count = 0
        async for message in interaction.channel.history(limit=100):
            if message.author == self.bot.user:
                await message.delete()
                deleted_count += 1
                if deleted_count >= count:
                    break
        
        await interaction.response.send_message(f"Deleted {deleted_count} messages.", ephemeral=True)
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

    @app_commands.command(name="total_messages")
    async def total_messages(self, interaction: discord.Interaction):
        """Shows the total number of messages stored in the database."""
        conn = await get_db_connection()
        try:
            async with conn.execute("SELECT COUNT(*) FROM messages") as cursor:
                total_count = await cursor.fetchone()
                await interaction.response.send_message(f"The total number of messages stored in the database is {total_count[0]}.")
        finally:
            await conn.close()
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

async def setup(bot):
    await bot.add_cog(MessageManagementCog(bot))