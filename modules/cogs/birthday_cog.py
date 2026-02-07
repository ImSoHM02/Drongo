import calendar

import discord
from discord import app_commands
from discord.ext import commands

from database_modules import birthdays


def _valid_date(month: int, day: int) -> bool:
    """Validate month/day combo using calendar monthrange."""
    if month < 1 or month > 12:
        return False
    try:
        _, max_day = calendar.monthrange(2000, month)  # leap-year safe baseline
    except Exception:
        return False
    return 1 <= day <= max_day


class BirthdayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    birthday = app_commands.Group(name="birthday", description="Manage your birthday")

    @birthday.command(name="set", description="Set your birthday (month/day) and timezone")
    @app_commands.describe(
        month="Month number (1-12)",
        day="Day of month",
        timezone="IANA timezone, e.g. America/New_York",
    )
    async def set_birthday(self, interaction: discord.Interaction, month: int, day: int, timezone: str):
        """Store or update the caller's birthday."""
        if not _valid_date(month, day):
            await interaction.response.send_message("Please provide a valid month/day.", ephemeral=True)
            return

        if not birthdays.validate_timezone(timezone):
            await interaction.response.send_message("Invalid timezone. Use an IANA name like `Europe/London`.", ephemeral=True)
            return

        await birthdays.set_birthday(str(interaction.guild_id), str(interaction.user.id), month, day, timezone)
        await interaction.response.send_message(
            f"Saved your birthday as {month:02d}-{day:02d} ({timezone}).",
            ephemeral=True,
        )
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    @birthday.command(name="view", description="View your saved birthday")
    async def view_birthday(self, interaction: discord.Interaction):
        record = await birthdays.get_birthday(str(interaction.guild_id), str(interaction.user.id))
        if not record:
            await interaction.response.send_message("You haven't set a birthday yet. Use `/birthday set`.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Birthday: {record['month']:02d}-{record['day']:02d} in {record['timezone']}.",
            ephemeral=True,
        )
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    @birthday.command(name="remove", description="Remove your saved birthday")
    async def remove_birthday(self, interaction: discord.Interaction):
        await birthdays.remove_birthday(str(interaction.guild_id), str(interaction.user.id))
        await interaction.response.send_message("Birthday removed.", ephemeral=True)
        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    @birthday.command(name="test", description="Trigger birthday announcements now")
    async def test_birthday(self, interaction: discord.Interaction):
        """Manually trigger the announcement loop for this guild."""
        # Restrict to admins/owner
        perms = interaction.user.guild_permissions
        is_admin = perms.administrator if perms else False
        is_owner = interaction.user.id == (self.bot.owner_id or 0)
        is_authorized = str(interaction.user.id) == getattr(self.bot, "authorized_user_id", "")

        if not (is_admin or is_owner or is_authorized):
            await interaction.response.send_message(
                "You need to be a server admin to run this.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            if hasattr(self.bot, "_announce_birthdays"):
                await self.bot._announce_birthdays()
                await interaction.followup.send("Birthday announcements run.", ephemeral=True)
            else:
                await interaction.followup.send("Announcer not available on this bot instance.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error running announcer: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(BirthdayCog(bot))
