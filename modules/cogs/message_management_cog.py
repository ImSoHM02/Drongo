import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from database_modules.database_schema import get_guild_db_path

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
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    @app_commands.command(name="total_messages")
    async def total_messages(self, interaction: discord.Interaction):
        """Shows the total number of messages stored in the database."""
        total_count = 0
        for guild in self.bot.guilds:
            db_path = get_guild_db_path(str(guild.id))
            if os.path.isfile(db_path):
                async with aiosqlite.connect(db_path) as conn:
                    async with conn.execute("SELECT COUNT(*) FROM messages") as cursor:
                        row = await cursor.fetchone()
                        total_count += row[0] if row else 0

        await interaction.response.send_message(f"The total number of messages stored across all guilds is {total_count}.")
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

async def setup(bot):
    await bot.add_cog(MessageManagementCog(bot))
