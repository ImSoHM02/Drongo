import calendar
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo

from database_modules import birthdays


def _valid_date(month: int, day: int) -> bool:
    if month < 1 or month > 12:
        return False
    try:
        _, max_day = calendar.monthrange(2000, month)
    except Exception:
        return False
    return 1 <= day <= max_day


class BirthdayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.birthday_announcer.start()

    async def cog_unload(self):
        self.birthday_announcer.cancel()

    @tasks.loop(hours=1)
    async def birthday_announcer(self):
        try:
            await self._announce_birthdays()
        except Exception as e:
            logging.error(f"Error in birthday announcer: {e}")

    @birthday_announcer.before_loop
    async def before_birthday_announcer(self):
        await self.bot.wait_until_ready()

    async def _announce_birthdays(self):
        """Announce birthdays for all guilds based on user timezones."""
        if not self.bot.guilds:
            return

        for guild in self.bot.guilds:
            try:
                records = await birthdays.get_all_birthdays(str(guild.id))
            except Exception as e:
                logging.error(f"Failed to load birthdays for guild {guild.id}: {e}")
                continue

            if not records:
                continue

            try:
                settings = await birthdays.get_birthday_settings(str(guild.id))
            except Exception as e:
                logging.error(f"Failed to load birthday settings for guild {guild.id}: {e}")
                settings = {"channel_id": None, "message_template": "Happy birthday, {user}! \U0001f382"}

            for record in records:
                tz_name = record.get("timezone")
                try:
                    tz = ZoneInfo(tz_name)
                except Exception:
                    continue

                today = discord.utils.utcnow().astimezone(tz).date()
                if today.month != record.get("month") or today.day != record.get("day"):
                    continue

                last_year = record.get("last_announced_year")
                if last_year and last_year >= today.year:
                    continue

                member = guild.get_member(int(record["user_id"]))
                if not member:
                    try:
                        member = await guild.fetch_member(int(record["user_id"]))
                    except Exception:
                        member = None

                target_channel = None
                if settings.get("channel_id"):
                    target_channel = guild.get_channel(int(settings["channel_id"]))

                if not target_channel:
                    target_channel = guild.system_channel
                if not target_channel:
                    target_channel = next(
                        (c for c in guild.text_channels if c.permissions_for(guild.me).send_messages),
                        None,
                    )
                if not target_channel:
                    continue

                template = settings.get("message_template") or "Happy birthday, {user}! \U0001f382"
                mention = member.mention if member else f"<@{record['user_id']}>"
                display = member.display_name if member else f"User {record['user_id']}"
                message = (
                    template.replace("{user}", mention)
                    .replace("{mention}", mention)
                    .replace("{username}", display)
                )

                try:
                    await target_channel.send(message)
                    await birthdays.mark_announced(str(guild.id), record["user_id"], today.year)
                    if hasattr(self.bot, "dashboard_manager"):
                        self.bot.dashboard_manager.log_event(
                            f"Sent birthday message for user {record['user_id']} in guild {guild.id}"
                        )
                except Exception as e:
                    logging.error(f"Failed to send birthday message in guild {guild.id}: {e}")

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
            await self._announce_birthdays()
            await interaction.followup.send("Birthday announcements run.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error running announcer: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(BirthdayCog(bot))
