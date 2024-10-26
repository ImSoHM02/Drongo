# modules/message_stats.py

import discord
from discord import app_commands
from database import get_db_connection, count_attachments, count_links
from modules.stats_display import StatsDisplay

class MessageStats(app_commands.Group):
    def __init__(self, bot):
        super().__init__(name="stats")
        self.bot = bot

    @app_commands.command(name="attachments")
    @app_commands.describe(user="The user whose attachment count to retrieve")
    async def count_attachments_command(self, interaction: discord.Interaction, user: discord.User):
        await count_attachments_cmd(interaction, user)
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

    @app_commands.command(name="links")
    @app_commands.describe(user="The user whose link count to retrieve")
    async def count_links_command(self, interaction: discord.Interaction, user: discord.User):
        await count_links_cmd(interaction, user)
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

async def count_attachments_cmd(interaction: discord.Interaction, user: discord.User):
    conn = await get_db_connection()
    try:
        attachment_count = await count_attachments(conn, str(user.id), str(interaction.guild_id))
        await interaction.response.send_message(f"{user.name} has posted {attachment_count} attachments in this server.")
    finally:
        await conn.close()

async def count_links_cmd(interaction: discord.Interaction, user: discord.User):
    conn = await get_db_connection()
    try:
        link_count = await count_links(conn, str(user.id), str(interaction.guild_id))
        await interaction.response.send_message(f"{user.name} has posted {link_count} links in this server.")
    finally:
        await conn.close()

def setup(bot):
    bot.tree.add_command(MessageStats(bot))