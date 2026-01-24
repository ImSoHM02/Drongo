import discord
from discord.ext import commands
from discord import app_commands
from modules.leveling_system import get_leveling_system
from typing import Optional

class LevelingCog(commands.Cog):
    """Commands for the leveling system."""
    
    def __init__(self, bot):
        self.bot = bot
        self.leveling_system = get_leveling_system(bot)
        bot.logger.info("LevelingCog initialized - level command group should be available")

    level = app_commands.Group(name="level", description="Commands for the leveling system")

    @level.command(name="stats")
    async def level_stats(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        """View your or another user's level statistics."""
        target_user = user or interaction.user
        
        try:
            user_data = await self.leveling_system.get_user_level_data(
                str(target_user.id), str(interaction.guild_id)
            )
            
            if not user_data:
                if target_user == interaction.user:
                    await interaction.response.send_message(
                        "You haven't earned any XP yet! Start chatting to begin leveling up! 🎮",
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f"{target_user.display_name} hasn't earned any XP yet.",
                        ephemeral=True
                    )
                return

            current_level = user_data['current_level']
            current_xp = user_data['current_xp']
            total_xp = user_data['total_xp']
            messages_sent = user_data['messages_sent']
            
            # Calculate XP for next level
            xp_needed, progress = self.leveling_system.get_xp_for_next_level(current_level, current_xp)
            next_level_total_xp = self.leveling_system.get_xp_required_for_level(current_level + 1)
            
            # Get rank information
            rank_info = await self.leveling_system.get_user_rank(
                str(target_user.id), str(interaction.guild_id)
            )
            
            # Create embed
            embed = discord.Embed(
                title=f"📊 {target_user.display_name}'s Level Stats",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🏆 Current Level",
                value=f"**{current_level}**",
                inline=True
            )
            
            embed.add_field(
                name="⭐ Total XP",
                value=f"**{total_xp:,}**",
                inline=True
            )
            
            if rank_info and rank_info.get('server_rank'):
                embed.add_field(
                    name="🥇 Server Rank",
                    value=f"**#{rank_info['server_rank']}**",
                    inline=True
                )
            
            embed.add_field(
                name="📈 Progress to Next Level",
                value=f"**{current_xp}/{next_level_total_xp - self.leveling_system.get_xp_required_for_level(current_level)}** XP\n"
                      f"({progress}% complete)\n"
                      f"*{xp_needed} XP remaining*",
                inline=False
            )
            
            embed.add_field(
                name="💬 Messages Sent",
                value=f"**{messages_sent:,}**",
                inline=True
            )
            
            embed.add_field(
                name="📅 Daily XP Earned",
                value=f"**{user_data.get('daily_xp_earned', 0)}**",
                inline=True
            )
            
            # Add rank title if available
            if rank_info and rank_info.get('rank_title'):
                embed.add_field(
                    name="🎖️ Current Rank",
                    value=f"**{rank_info['rank_title']}**",
                    inline=True
                )
            
            # Add range name if available
            range_info = await self.leveling_system.get_user_range(
                str(target_user.id), str(interaction.guild_id)
            )
            if range_info:
                embed.add_field(
                    name="🏅 Rank Tier",
                    value=f"**{range_info['name']}**",
                    inline=True
                )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while fetching level stats.", ephemeral=True
            )

    @level.command(name="leaderboard")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = 10):
        """View the server's XP leaderboard."""
        limit = min(max(limit, 1), 20)  # Clamp between 1 and 20
        
        try:
            leaderboard = await self.leveling_system.get_leaderboard(
                str(interaction.guild_id), limit
            )
            
            if not leaderboard:
                await interaction.response.send_message(
                    "No one has earned XP yet! Be the first to start chatting! 🎮",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"🏆 {interaction.guild.name} Leaderboard",
                description="Top users by total XP",
                color=discord.Color.gold()
            )
            
            leaderboard_text = []
            for i, entry in enumerate(leaderboard, 1):
                user = self.bot.get_user(int(entry['user_id']))
                if user:
                    name = user.display_name
                else:
                    name = f"Unknown User ({entry['user_id'][:8]}...)"
                
                # Get rank information for this user
                rank_info = await self.leveling_system.get_user_rank(
                    entry['user_id'], str(interaction.guild_id)
                )
                
                # Add medal emojis for top 3
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈"
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"**{i}.**"
                
                # Include rank title if available
                rank_display = ""
                if rank_info and rank_info.get('rank_title'):
                    emoji_prefix = f"{rank_info.get('emoji', '')} " if rank_info.get('emoji') else ""
                    rank_display = f" • {emoji_prefix}{rank_info['rank_title']}"
                
                # Add range name if available
                range_display = ""
                if entry.get('range_name'):
                    range_display = f" • 🏅 {entry['range_name']}"
                
                leaderboard_text.append(
                    f"{medal} {name}\n"
                    f"   Level {entry['current_level']} • {entry['total_xp']:,} XP{rank_display}{range_display}"
                )
            
            embed.description = "\n\n".join(leaderboard_text)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while fetching the leaderboard.", ephemeral=True
            )
async def setup(bot):
    bot.logger.info("Setting up LevelingCog...")
    await bot.add_cog(LevelingCog(bot))
    bot.logger.info("LevelingCog added successfully")
