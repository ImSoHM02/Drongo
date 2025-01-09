import discord
from discord import app_commands
from discord.ext import commands
import os

AUTHORIZED_USER_ID = int(os.getenv('AUTHORIZED_USER_ID'))

async def clear_achievements(interaction: discord.Interaction, user: discord.User, bot):
    # Check if the command user is authorized
    if interaction.user.id != AUTHORIZED_USER_ID:
        await interaction.response.send_message(
            "You are not authorized to use this command.",
            ephemeral=True
        )
        return
        
    # Clear the user's achievements
    bot.achievement_system.clear_user_achievements(user.id)
    
    await interaction.response.send_message(
        f"Successfully cleared all achievements for user {user.name}.",
        ephemeral=True
    )

async def achievements(interaction: discord.Interaction, bot):
    earned_achievements, total_achievements = bot.achievement_system.get_user_achievements(interaction.user.id)
    
    if not earned_achievements:
        await interaction.response.send_message(
            f"You haven't earned any achievements yet! There are {total_achievements} achievements to discover.",
            ephemeral=True
        )
        return
    
    # Create the achievements list message
    achievements_text = "\n".join([
        f"> 🏆 **{achievement.name}** ({achievement.points} points)"
        for achievement in earned_achievements
    ])
    
    remaining = total_achievements - len(earned_achievements)
    # Calculate total points
    total_points = sum(achievement.points for achievement in earned_achievements)
    status = f"You've earned {len(earned_achievements)} achievement{'s' if len(earned_achievements) != 1 else ''} worth {total_points} points!"
    if remaining > 0:
        status += f" There {'is' if remaining == 1 else 'are'} {remaining} more to discover!"
    
    await interaction.response.send_message(
        f"{status}\n\n{achievements_text}",
        ephemeral=True
    )

async def leaderboard(interaction: discord.Interaction, bot):
    """Display the achievement leaderboard."""
    leaderboard_data = await bot.achievement_system.get_leaderboard(interaction.guild)
    
    if not leaderboard_data:
        embed = discord.Embed(
            title="🏆 Achievement Leaderboard",
            description="No achievements have been earned yet!",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Create the leaderboard embed
    embed = discord.Embed(
        title="🏆 Achievement Leaderboard",
        color=discord.Color.gold()
    )
    
    # Add medal emojis for top 3
    medals = ["🥇", "🥈", "🥉"]
    
    # Calculate total achievements and points across all users
    total_points = sum(points for _, points, _ in leaderboard_data)
    total_achievements = sum(count for _, _, count in leaderboard_data)
    
    # Add summary field
    embed.add_field(
        name="Server Stats",
        value=f"Total Points: {total_points:,}\nTotal Achievements: {total_achievements:,}",
        inline=False
    )
    
    # Add leaderboard entries
    leaderboard_text = ""
    for i, (member, points, count) in enumerate(leaderboard_data[:10]):  # Show top 10
        prefix = medals[i] if i < 3 else "👤"
        leaderboard_text += f"{prefix} **{member.display_name}**\n{points:,} points ({count:,} achievements)\n\n"
    
    embed.add_field(
        name="Top 10 Achievers",
        value=leaderboard_text.strip() or "No achievements yet!",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

def setup(bot):
    @bot.tree.command(
        name="clear_achievements",
        description="Clear achievements for a specified user (Admin only)"
    )
    @app_commands.describe(user="The user whose achievements should be cleared")
    async def clear_achievements_command(interaction: discord.Interaction, user: discord.User):
        await clear_achievements(interaction, user, bot)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(
        name="achievements",
        description="Check your achievement progress"
    )
    async def achievements_command(interaction: discord.Interaction):
        await achievements(interaction, bot)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(
        name="achievement_leaderboard",
        description="View the achievement leaderboard"
    )
    async def leaderboard_command(interaction: discord.Interaction):
        await leaderboard(interaction, bot)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)
