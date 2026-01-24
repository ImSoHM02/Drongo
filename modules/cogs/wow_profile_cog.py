import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from blizzardapi2.wow.wow_profile_api import WowProfileApi


class WoWProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.region_locales = {
            "us": "en_US",
            "eu": "en_GB",
            "kr": "ko_KR",
            "tw": "zh_TW",
        }
        client_id = os.getenv("WOW_CLIENT_ID")
        client_secret = os.getenv("WOW_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("WoW API credentials not configured (WOW_CLIENT_ID / WOW_CLIENT_SECRET)")
        self.api = WowProfileApi(client_id, client_secret)

    @app_commands.command(name="wow_profile")
    @app_commands.describe(
        region="Region code (us, eu, kr, tw)",
        realm="Realm name or slug",
        character="Character name",
    )
    async def wow_profile(self, interaction: discord.Interaction, region: str, realm: str, character: str):
        """Lookup a World of Warcraft character profile."""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=True)
        except discord.NotFound:
            return

        region = region.lower()
        if region not in {"us", "eu", "kr", "tw"}:
            await interaction.followup.send("Invalid region. Use one of: us, eu, kr, tw.", ephemeral=True)
            return

        realm_slug = realm.strip().lower().replace(" ", "-")
        char_slug = character.strip().lower()
        locale = self.region_locales.get(region, "en_US")

        try:
            # blizzardapi2 is synchronous; run in a thread to avoid blocking.
            profile = await asyncio.to_thread(
                self.api.get_character_profile_summary, region, locale, realm_slug, char_slug
            )
            equipment = await asyncio.to_thread(
                self.api.get_character_equipment_summary, region, locale, realm_slug, char_slug
            )
            media = await asyncio.to_thread(
                self.api.get_character_media_summary, region, locale, realm_slug, char_slug
            )
        except Exception as e:
            await interaction.followup.send(f"Error calling Blizzard API: {e}")
            return

        level = profile.get("level")
        class_name = (profile.get("character_class") or {}).get("name", "Unknown")
        ilvl = profile.get("equipped_item_level") or equipment.get("equipped_item_level")
        name = profile.get("name", character)
        realm_name = (profile.get("realm") or {}).get("name", realm)
        race = (profile.get("race") or {}).get("name", "Unknown")
        faction = (profile.get("faction") or {}).get("name", "Unknown")
        achievement_points = profile.get("achievement_points")

        avatar_url = None
        if isinstance(media, dict):
            assets = media.get("assets") or []
            for asset in assets:
                if asset.get("key") in {"avatar", "main-raw", "main"}:
                    avatar_url = asset.get("value")
                    break

        embed = discord.Embed(
            title=f"{name} - {realm_name} ({region.upper()})",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Level", value=str(level) if level is not None else "Unknown", inline=True)
        embed.add_field(name="Race / Class", value=f"{race} / {class_name}", inline=True)
        embed.add_field(name="Equipped iLvl", value=str(ilvl) if ilvl is not None else "Unknown", inline=True)
        embed.add_field(name="Faction", value=faction, inline=True)
        if achievement_points is not None:
            embed.add_field(name="Achievement Points", value=str(achievement_points), inline=True)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        await interaction.followup.send(embed=embed)

        # Persist profile snapshot for future leaderboards
        try:
            if interaction.guild:
                await upsert_profile(
                    guild_id=str(interaction.guild.id),
                    region=region,
                    realm_slug=realm_slug,
                    character_slug=char_slug,
                    character_name=name,
                    race=race,
                    character_class=class_name,
                    faction=faction,
                    level=level,
                    equipped_ilvl=ilvl,
                    achievement_points=achievement_points,
                    raw_profile=None,
                    raw_equipment=None,
                )
        except Exception as e:
            self.bot.logger.error(f"Failed to persist WoW profile for {name}@{realm_slug}: {e}")

        if hasattr(self.bot, "dashboard_manager"):
            self.bot.dashboard_manager.increment_command_count()


async def setup(bot):
    await bot.add_cog(WoWProfileCog(bot))
