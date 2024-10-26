import discord
from discord import app_commands
import aiohttp
import zipfile
import io

async def download_emojis(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        # Download emojis
        emoji_data = []
        for emoji in interaction.guild.emojis:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(emoji.url)) as resp:
                    if resp.status == 200:
                        emoji_data.append((f"{emoji.name}.{'gif' if emoji.animated else 'png'}", await resp.read()))

        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, data in emoji_data:
                zip_file.writestr(filename, data)

        zip_buffer.seek(0)
        
        # Send zip file as attachment
        await interaction.followup.send("Here are all the emojis from this server:", 
                       file=discord.File(zip_buffer, filename="server_emojis.zip"))
    except Exception as e:
        await interaction.followup.send(f"An error occurred: {str(e)}")

def setup(bot):
    @bot.tree.command(name="download_emojis")
    @app_commands.checks.has_permissions(manage_emojis=True)
    @app_commands.describe(
        confirm="Type 'yes' to confirm downloading all server emojis"
    )
    async def download_emojis_command(interaction: discord.Interaction, confirm: str):
        if confirm.lower() != 'yes':
            await interaction.response.send_message("Command cancelled. Please type 'yes' to confirm.")
            return
        await download_emojis(interaction)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    return download_emojis_command  # Return the command function