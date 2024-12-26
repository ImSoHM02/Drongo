import discord
from discord import app_commands
from discord.ext import commands

def setup(bot):
    @bot.tree.command(
        name="achievements",
        description="Check your achievement progress"
    )
    async def achievements(interaction: discord.Interaction):
        earned_achievements, total_achievements = bot.achievement_system.get_user_achievements(interaction.user.id)
        
        if not earned_achievements:
            await interaction.response.send_message(
                f"You haven't earned any achievements yet! There are {total_achievements} achievements to discover.",
                ephemeral=True
            )
            return
        
        # Create the achievements list message
        achievements_text = "\n".join([
            f"> 🏆 **{achievement.name}**\n> ```\n> {achievement.description}\n> ```"
            for achievement in earned_achievements
        ])
        
        remaining = total_achievements - len(earned_achievements)
        status = f"You've earned {len(earned_achievements)} achievement{'s' if len(earned_achievements) != 1 else ''}!"
        if remaining > 0:
            status += f" There {'is' if remaining == 1 else 'are'} {remaining} more to discover!"
        
        await interaction.response.send_message(
            f"{status}\n\n{achievements_text}",
            ephemeral=True
        )
