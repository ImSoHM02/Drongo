import os
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime


class FeatureRequestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="feature", description="Request a new feature for the bot")
    @app_commands.describe(title="Brief title for your feature request", description="Detailed description of the feature you'd like to see")
    async def feature_request(self, interaction: discord.Interaction, title: str, description: str):
        """Submit a feature request that gets sent to the bot owner."""
        authorized_user_id = int(os.getenv("AUTHORIZED_USER_ID"))

        try:
            owner = await self.bot.fetch_user(authorized_user_id)
        except discord.NotFound:
            await interaction.response.send_message(
                "Unable to submit feature request. Please try again later.",
                ephemeral=True
            )
            return

        # Create formatted embed for the DM
        embed = discord.Embed(
            title="New Feature Request",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Title", value=title, inline=False)
        embed.add_field(name="Description", value=description, inline=False)
        embed.add_field(name="Requested By", value=f"{interaction.user} ({interaction.user.id})", inline=True)
        embed.add_field(name="Server", value=f"{interaction.guild.name}" if interaction.guild else "DM", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        try:
            await owner.send(embed=embed)
            await interaction.response.send_message(
                "Your feature request has been submitted. Thanks for the feedback!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Unable to send the feature request. The bot owner may have DMs disabled.",
                ephemeral=True
            )

        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()


async def setup(bot):
    await bot.add_cog(FeatureRequestCog(bot))
