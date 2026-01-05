import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import os
from database_schema import get_guild_db_path

class MessageStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    stats = app_commands.Group(name="stats", description="Commands to get message statistics")

    @stats.command(name="attachments")
    @app_commands.describe(user="The user whose attachment count to retrieve")
    async def count_attachments_command(self, interaction: discord.Interaction, user: discord.User):
        """Counts the number of attachments a user has posted."""
        db_path = get_guild_db_path(str(interaction.guild_id))
        if not os.path.isfile(db_path):
            await interaction.response.send_message("No chat history found for this server.")
            return

        async with aiosqlite.connect(db_path) as conn:
            async with conn.execute("SELECT message_content FROM messages WHERE user_id=?", (str(user.id),)) as cursor:
                messages = await cursor.fetchall()
                attachment_count = 0
                for (content,) in messages:
                    attachment_count += content.count("https://cdn.discordapp.com/attachments/")

        await interaction.response.send_message(f"{user.name} has posted {attachment_count} attachments in this server.")
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    @stats.command(name="links")
    @app_commands.describe(user="The user whose link count to retrieve")
    async def count_links_command(self, interaction: discord.Interaction, user: discord.User):
        """Counts the number of links a user has posted."""
        db_path = get_guild_db_path(str(interaction.guild_id))
        if not os.path.isfile(db_path):
            await interaction.response.send_message("No chat history found for this server.")
            return

        async with aiosqlite.connect(db_path) as conn:
            async with conn.execute("SELECT message_content FROM messages WHERE user_id=?", (str(user.id),)) as cursor:
                messages = await cursor.fetchall()
                link_count = 0
                for (content,) in messages:
                    # Count all links minus Discord attachment links
                    links = [part for part in content.split() if part.startswith("http")]
                    for url in links:
                        if not url.startswith("https://cdn.discordapp.com/attachments/"):
                            link_count += 1

        await interaction.response.send_message(f"{user.name} has posted {link_count} links in this server.")
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

async def setup(bot):
    await bot.add_cog(MessageStatsCog(bot))
