import discord
from discord.ext import commands
from discord import app_commands
from database import get_db_connection, count_attachments, count_links

class MessageStatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    stats = app_commands.Group(name="stats", description="Commands to get message statistics")

    @stats.command(name="attachments")
    @app_commands.describe(user="The user whose attachment count to retrieve")
    async def count_attachments_command(self, interaction: discord.Interaction, user: discord.User):
        """Counts the number of attachments a user has posted."""
        conn = await get_db_connection()
        try:
            attachment_count = await count_attachments(conn, str(user.id), str(interaction.guild_id))
            await interaction.response.send_message(f"{user.name} has posted {attachment_count} attachments in this server.")
        finally:
            await conn.close()
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

    @stats.command(name="links")
    @app_commands.describe(user="The user whose link count to retrieve")
    async def count_links_command(self, interaction: discord.Interaction, user: discord.User):
        """Counts the number of links a user has posted."""
        conn = await get_db_connection()
        try:
            link_count = await count_links(conn, str(user.id), str(interaction.guild_id))
            await interaction.response.send_message(f"{user.name} has posted {link_count} links in this server.")
        finally:
            await conn.close()
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

async def setup(bot):
    await bot.add_cog(MessageStatsCog(bot))