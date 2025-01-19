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
    earned_ids = {a.id for a in earned_achievements}
    
    # Create embed for achievements display
    embed = discord.Embed(
        title="🏆 Achievements",
        color=discord.Color.gold()
    )
    
    # Calculate total points
    total_points = sum(achievement.points for achievement in earned_achievements)
    
    # Add earned achievements section
    if earned_achievements:
        earned_text = ""
        for achievement in earned_achievements:
            points_text = f"{achievement.points} points"
            if hasattr(achievement, 'is_first_discoverer') and achievement.is_first_discoverer:
                points_text += " 🥇 First Discoverer!"
            earned_text += f"> 🏆 **{achievement.name}** ({points_text})\n"
            if achievement.description:
                earned_text += f"> *{achievement.description}*\n"
            earned_text += "\n"
        embed.add_field(name="Earned Achievements", value=earned_text.strip(), inline=False)
    
    # Add available achievements section (including hints for hidden ones)
    available_text = ""
    for achievement_id, achievement in bot.achievement_system.achievements.items():
        if achievement_id not in earned_ids:
            if achievement.hidden:
                if achievement.hint:
                    available_text += f"> ❓ **???** - *{achievement.hint}*\n\n"
            else:
                available_text += f"> ⭕ **{achievement.name}** ({achievement.points} points)\n\n"
    
    if available_text:
        embed.add_field(name="Available Achievements", value=available_text.strip(), inline=False)
    
    # Add summary
    visible_total = sum(1 for a in bot.achievement_system.achievements.values()
                       if not a.hidden or a.id in earned_ids)
    status = f"You've earned {len(earned_achievements)} achievement{'s' if len(earned_achievements) != 1 else ''} worth {total_points} points!"
    remaining = visible_total - len(earned_achievements)
    if remaining > 0:
        status += f"\nThere {'is' if remaining == 1 else 'are'} {remaining} more to discover!"
        if any(a.hidden and a.id not in earned_ids for a in bot.achievement_system.achievements.values()):
            status += "\n(Some achievements are hidden until discovered!)"
    
    embed.description = status
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
