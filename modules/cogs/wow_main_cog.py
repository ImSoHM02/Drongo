import discord
from discord.ext import commands
from discord import app_commands

from database_modules.wow_main_registry import set_main, get_main


class WoWMainCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="wow_setmain")
    @app_commands.describe(
        region="Region code (us, eu, kr, tw)",
        realm="Realm name or slug",
        character="Character name",
    )
    async def wow_setmain(self, interaction: discord.Interaction, region: str, realm: str, character: str):
        """Set your main WoW character for this server."""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            return

        region = region.lower()
        if region not in {"us", "eu", "kr", "tw"}:
            await interaction.followup.send("Invalid region. Use one of: us, eu, kr, tw.", ephemeral=True)
            return

        realm_slug = realm.strip().lower().replace(" ", "-")
        char_slug = character.strip().lower()

        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            return

        await set_main(
            guild_id=str(interaction.guild.id),
            discord_user_id=str(interaction.user.id),
            region=region,
            realm_slug=realm_slug,
            character_slug=char_slug,
        )

        await interaction.followup.send(
            f"Main set to **{character}** on **{realm}** ({region.upper()}). You can change this anytime.",
            ephemeral=True,
        )

    @app_commands.command(name="wow_getmain")
    async def wow_getmain(self, interaction: discord.Interaction):
        """Show your registered main character for this server."""
        if not interaction.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        main = await get_main(str(interaction.guild.id), str(interaction.user.id))
        if not main:
            await interaction.response.send_message("No main registered yet. Set one with /wow_setmain.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Your main is **{main['character_slug']}** on **{main['realm_slug']}** ({main['region'].upper()}).",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(WoWMainCog(bot))
