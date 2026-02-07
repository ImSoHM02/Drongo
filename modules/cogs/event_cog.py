import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo

from database_modules import events
from database_modules.birthdays import validate_timezone


class EventJoinView(discord.ui.View):
    """Persistent view with Join/Leave buttons for events."""

    def __init__(self, guild_id: str, event_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.event_id = event_id

    @discord.ui.button(label="Join Event", style=discord.ButtonStyle.green,
                       custom_id="event_join")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        # Parse event_id from the message embed footer
        event_id = self._parse_event_id(interaction.message)
        if event_id is None:
            await interaction.followup.send("Could not determine the event.", ephemeral=True)
            return

        event = await events.get_event(guild_id, event_id)
        if not event or event["cancelled"]:
            await interaction.followup.send("This event has been cancelled.", ephemeral=True)
            return

        now_ts = int(discord.utils.utcnow().timestamp())
        if event["event_timestamp"] <= now_ts:
            await interaction.followup.send("This event has already passed.", ephemeral=True)
            return

        await events.add_attendee(guild_id, event_id, str(interaction.user.id))
        await interaction.followup.send("You've joined the event!", ephemeral=True)

        # Update the embed with the new attendee list
        await self._update_embed(interaction, guild_id, event_id, event)

    @discord.ui.button(label="Leave Event", style=discord.ButtonStyle.red,
                       custom_id="event_leave")
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild_id = str(interaction.guild_id)
        event_id = self._parse_event_id(interaction.message)
        if event_id is None:
            await interaction.followup.send("Could not determine the event.", ephemeral=True)
            return

        await events.remove_attendee(guild_id, event_id, str(interaction.user.id))
        await interaction.followup.send("You've left the event.", ephemeral=True)

        event = await events.get_event(guild_id, event_id)
        if event:
            await self._update_embed(interaction, guild_id, event_id, event)

    def _parse_event_id(self, message: discord.Message) -> int | None:
        """Extract event ID from the embed footer text."""
        if message.embeds:
            footer = message.embeds[0].footer
            if footer and footer.text:
                # Footer format: "Event ID: 123"
                try:
                    return int(footer.text.split("Event ID: ")[1])
                except (IndexError, ValueError):
                    pass
        return None

    async def _update_embed(self, interaction: discord.Interaction,
                            guild_id: str, event_id: int, event: dict):
        """Rebuild and edit the event embed with current attendees."""
        attendee_ids = await events.get_attendees(guild_id, event_id)
        embed = build_event_embed(event, attendee_ids)
        try:
            await interaction.message.edit(embed=embed)
        except discord.HTTPException:
            pass


def build_event_embed(event: dict, attendee_ids: list[str]) -> discord.Embed:
    """Build a formatted embed for an event."""
    ts = event["event_timestamp"]
    cancelled = event.get("cancelled", 0)

    if cancelled:
        title = f"~~{event['title']}~~ (CANCELLED)"
        colour = discord.Colour.dark_grey()
    else:
        title = event["title"]
        colour = discord.Colour.blue()

    embed = discord.Embed(title=title, colour=colour)

    if event.get("description"):
        embed.description = event["description"]

    embed.add_field(
        name="When",
        value=f"<t:{ts}:F>\n<t:{ts}:R>",
        inline=False,
    )

    embed.add_field(
        name="Created by",
        value=f"<@{event['creator_id']}>",
        inline=True,
    )

    if attendee_ids:
        mentions = ", ".join(f"<@{uid}>" for uid in attendee_ids)
        embed.add_field(
            name=f"Attendees ({len(attendee_ids)})",
            value=mentions,
            inline=False,
        )
    else:
        embed.add_field(
            name="Attendees (0)",
            value="No one has joined yet.",
            inline=False,
        )

    embed.set_footer(text=f"Event ID: {event['id']}")
    return embed


class EventCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Register the persistent view so buttons work after restart
        self.bot.add_view(EventJoinView("0", 0))

    async def cog_load(self):
        self.event_reminder.start()

    async def cog_unload(self):
        self.event_reminder.cancel()

    # ------------------------------------------------------------------
    # Slash commands
    # ------------------------------------------------------------------
    event = app_commands.Group(name="event", description="Create and manage events")

    @event.command(name="create", description="Create a new event")
    @app_commands.describe(
        title="Event title",
        year="Year (e.g. 2026)",
        month="Month (1-12)",
        day="Day of month",
        hour="Hour (0-23)",
        minute="Minute (0-59)",
        timezone="IANA timezone, e.g. America/New_York",
        description="Optional event description",
    )
    async def create_event(self, interaction: discord.Interaction,
                           title: str, year: int, month: int, day: int,
                           hour: int, minute: int, timezone: str,
                           description: str = None):
        if not validate_timezone(timezone):
            await interaction.response.send_message(
                "Invalid timezone. Use an IANA name like `America/New_York`.",
                ephemeral=True,
            )
            return

        try:
            tz = ZoneInfo(timezone)
            local_dt = datetime(year, month, day, hour, minute, tzinfo=tz)
        except (ValueError, OverflowError):
            await interaction.response.send_message(
                "Invalid date/time. Please check your values.", ephemeral=True,
            )
            return

        unix_ts = int(local_dt.timestamp())
        now_ts = int(discord.utils.utcnow().timestamp())

        if unix_ts <= now_ts:
            await interaction.response.send_message(
                "The event time must be in the future.", ephemeral=True,
            )
            return

        guild_id = str(interaction.guild_id)
        event_id = await events.create_event(
            guild_id, str(interaction.user.id), title, description, unix_ts,
        )

        # Auto-add creator as attendee
        await events.add_attendee(guild_id, event_id, str(interaction.user.id))
        attendee_ids = [str(interaction.user.id)]

        event_data = await events.get_event(guild_id, event_id)
        embed = build_event_embed(event_data, attendee_ids)
        view = EventJoinView(guild_id, event_id)

        await interaction.response.send_message(embed=embed, view=view)

        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    @event.command(name="cancel", description="Cancel an event you created")
    @app_commands.describe(event_id="The ID of the event to cancel (shown in the embed footer)")
    async def cancel_event(self, interaction: discord.Interaction, event_id: int):
        guild_id = str(interaction.guild_id)
        event_data = await events.get_event(guild_id, event_id)

        if not event_data:
            await interaction.response.send_message("Event not found.", ephemeral=True)
            return

        if event_data["cancelled"]:
            await interaction.response.send_message("This event is already cancelled.", ephemeral=True)
            return

        # Only creator or admin can cancel
        perms = interaction.user.guild_permissions
        is_admin = perms.administrator if perms else False
        is_creator = str(interaction.user.id) == event_data["creator_id"]
        is_authorized = str(interaction.user.id) == getattr(self.bot, "authorized_user_id", "")

        if not (is_creator or is_admin or is_authorized):
            await interaction.response.send_message(
                "Only the event creator or a server admin can cancel this event.",
                ephemeral=True,
            )
            return

        await events.cancel_event(guild_id, event_id)

        attendee_ids = await events.get_attendees(guild_id, event_id)
        event_data["cancelled"] = 1
        embed = build_event_embed(event_data, attendee_ids)

        await interaction.response.send_message(
            f"Event **{event_data['title']}** has been cancelled.", embed=embed,
        )

        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    @event.command(name="list", description="List upcoming events for this server")
    async def list_events(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        now_ts = int(discord.utils.utcnow().timestamp())
        upcoming = await events.get_upcoming_events(guild_id, now_ts)

        if not upcoming:
            await interaction.response.send_message("No upcoming events.", ephemeral=True)
            return

        embed = discord.Embed(title="Upcoming Events", colour=discord.Colour.blue())
        for ev in upcoming[:10]:
            ts = ev["event_timestamp"]
            attendee_ids = await events.get_attendees(guild_id, ev["id"])
            embed.add_field(
                name=f"{ev['title']} (ID: {ev['id']})",
                value=f"<t:{ts}:F> (<t:{ts}:R>)\nAttendees: {len(attendee_ids)}",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()

    # ------------------------------------------------------------------
    # Background reminder task
    # ------------------------------------------------------------------
    @tasks.loop(minutes=1)
    async def event_reminder(self):
        try:
            await self._send_reminders()
        except Exception as e:
            logging.error(f"Error in event reminder: {e}")

    @event_reminder.before_loop
    async def before_event_reminder(self):
        await self.bot.wait_until_ready()

    async def _send_reminders(self):
        if not self.bot.guilds:
            return

        now_ts = int(discord.utils.utcnow().timestamp())
        window_ts = now_ts + 3600  # 1 hour from now

        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            try:
                pending = await events.get_events_needing_reminder(guild_id, now_ts, window_ts)
            except Exception as e:
                logging.error(f"Failed to load events for guild {guild.id}: {e}")
                continue

            if not pending:
                continue

            try:
                settings = await events.get_event_settings(guild_id)
            except Exception as e:
                logging.error(f"Failed to load event settings for guild {guild.id}: {e}")
                settings = {"channel_id": None}

            # Resolve target channel
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

            for ev in pending:
                ts = ev["event_timestamp"]
                attendee_ids = await events.get_attendees(guild_id, ev["id"])

                mentions = " ".join(f"<@{uid}>" for uid in attendee_ids) if attendee_ids else ""

                embed = discord.Embed(
                    title=f"Event Reminder: {ev['title']}",
                    description=f"Starting <t:{ts}:R>!",
                    colour=discord.Colour.gold(),
                )
                embed.add_field(name="When", value=f"<t:{ts}:F>", inline=False)
                if attendee_ids:
                    embed.add_field(
                        name=f"Attendees ({len(attendee_ids)})",
                        value=", ".join(f"<@{uid}>" for uid in attendee_ids),
                        inline=False,
                    )
                embed.set_footer(text=f"Event ID: {ev['id']}")

                try:
                    await target_channel.send(content=mentions, embed=embed)
                    await events.mark_reminder_sent(guild_id, ev["id"])
                    if hasattr(self.bot, "dashboard_manager"):
                        self.bot.dashboard_manager.log_event(
                            f"Sent event reminder for '{ev['title']}' in guild {guild.id}"
                        )
                except Exception as e:
                    logging.error(f"Failed to send event reminder in guild {guild.id}: {e}")


async def setup(bot):
    await bot.add_cog(EventCog(bot))
