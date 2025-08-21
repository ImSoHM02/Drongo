import discord
from discord.ext import commands
from discord import app_commands
from modules.leveling_system import get_leveling_system
import json
from typing import Optional

class LevelingCog(commands.Cog):
    """Commands for the leveling system."""
    
    def __init__(self, bot):
        self.bot = bot
        self.leveling_system = get_leveling_system(bot)

    @app_commands.command(name="level")
    async def level_command(self, interaction: discord.Interaction, 
                           stats_user: Optional[discord.User] = None,
                           leaderboard_limit: Optional[int] = None,
                           config_setting: Optional[str] = None,
                           config_value: Optional[str] = None):
        """Handle level subcommands based on the interaction data."""
        
        # Extract the subcommand from the interaction
        subcommand = interaction.data.get('options', [{}])[0].get('name', 'stats')
        
        if subcommand == "stats":
            await self.level_stats(interaction, stats_user)
        elif subcommand == "leaderboard":
            await self.leaderboard(interaction, leaderboard_limit or 10)
        elif subcommand == "config":
            await self.configure_leveling(interaction, config_setting, config_value)
        elif subcommand == "view-config":
            await self.view_config(interaction)
        elif subcommand == "ranks":
            await self.manage_ranks(interaction)
        elif subcommand == "rewards":
            await self.manage_rewards(interaction)

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

    async def configure_leveling(self, interaction: discord.Interaction, setting: str, value: str):
        """Configure leveling system settings (Admin only)."""
        
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need administrator permissions to configure the leveling system.",
                ephemeral=True
            )
            return
        
        try:
            from database_pool import get_main_pool
            pool = await get_main_pool()
            
            # Validate and convert the value based on setting type
            if setting in ["enabled", "level_up_announcements", "dm_level_notifications"]:
                # Boolean settings
                if value.lower() in ["true", "1", "yes", "on", "enable"]:
                    db_value = 1
                    display_value = "Enabled"
                elif value.lower() in ["false", "0", "no", "off", "disable"]:
                    db_value = 0
                    display_value = "Disabled"
                else:
                    await interaction.response.send_message(
                        f"❌ Invalid value for {setting}. Use: true/false, 1/0, yes/no, on/off, enable/disable",
                        ephemeral=True
                    )
                    return
            elif setting in ["base_xp", "max_xp", "daily_xp_cap"]:
                # Integer settings
                try:
                    db_value = int(value)
                    if db_value < 0:
                        raise ValueError("Value must be positive")
                    display_value = str(db_value)
                except ValueError:
                    await interaction.response.send_message(
                        f"❌ Invalid value for {setting}. Must be a positive number.",
                        ephemeral=True
                    )
                    return
            elif setting == "announcement_channel":
                # Channel setting
                if value.lower() in ["none", "null", "disable", "0"]:
                    db_value = None
                    display_value = "None (use message channel)"
                else:
                    try:
                        # Try to parse channel mention or ID
                        channel_id = value.strip('<>#')
                        channel = interaction.guild.get_channel(int(channel_id))
                        if not channel:
                            await interaction.response.send_message(
                                f"❌ Channel not found. Please mention a valid channel or use the channel ID.",
                                ephemeral=True
                            )
                            return
                        db_value = str(channel.id)
                        display_value = f"{channel.mention}"
                    except ValueError:
                        await interaction.response.send_message(
                            f"❌ Invalid channel. Please mention a channel or use a channel ID.",
                            ephemeral=True
                        )
                        return
            
            # Update the configuration in database
            await pool.execute_write(f"""
                INSERT INTO leveling_config (guild_id, {setting}) 
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET 
                {setting} = excluded.{setting},
                updated_at = CURRENT_TIMESTAMP
            """, (str(interaction.guild_id), db_value))
            
            # Clear the cache so new config is loaded
            if hasattr(self.leveling_system, '_config_cache'):
                guild_id = str(interaction.guild_id)
                if guild_id in self.leveling_system._config_cache:
                    del self.leveling_system._config_cache[guild_id]
                if guild_id in self.leveling_system._cache_expiry:
                    del self.leveling_system._cache_expiry[guild_id]
            
            embed = discord.Embed(
                title="✅ Configuration Updated",
                description=f"**{setting.replace('_', ' ').title()}** has been set to: **{display_value}**",
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while updating the configuration.", ephemeral=True
            )

    async def view_config(self, interaction: discord.Interaction):
        """View current leveling system configuration."""
        
        try:
            config = await self.leveling_system.get_guild_config(str(interaction.guild_id))
            
            embed = discord.Embed(
                title="⚙️ Leveling System Configuration",
                color=discord.Color.blue()
            )
            
            # Basic settings
            embed.add_field(
                name="🔧 System Status",
                value="Enabled" if config.get('enabled') else "Disabled",
                inline=True
            )
            
            embed.add_field(
                name="⭐ XP per Message",
                value=f"{config.get('base_xp', 5)} - {config.get('max_xp', 25)} XP",
                inline=True
            )
            
            embed.add_field(
                name="📅 Daily XP Cap",
                value=f"{config.get('daily_xp_cap', 1000)} XP",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Cooldown",
                value=f"{config.get('min_cooldown_seconds', 30)}-{config.get('max_cooldown_seconds', 60)}s",
                inline=True
            )
            
            embed.add_field(
                name="📝 Message Requirements",
                value=f"Min {config.get('min_message_chars', 5)} chars, {config.get('min_message_words', 2)} words",
                inline=True
            )
            
            embed.add_field(
                name="🎉 Level Up Announcements",
                value="Enabled" if config.get('level_up_announcements') else "Disabled",
                inline=True
            )
            
            # Announcement channel
            announcement_channel_id = config.get('announcement_channel_id')
            if announcement_channel_id:
                channel = interaction.guild.get_channel(int(announcement_channel_id))
                channel_display = channel.mention if channel else "Unknown Channel"
            else:
                channel_display = "Message Channel"
            
            embed.add_field(
                name="📢 Announcement Channel",
                value=channel_display,
                inline=True
            )
            
            embed.add_field(
                name="📱 DM Notifications",
                value="Enabled" if config.get('dm_level_notifications') else "Disabled",
                inline=True
            )
            
            # Channel restrictions
            blacklist = json.loads(config.get('blacklisted_channels', '[]'))
            whitelist = json.loads(config.get('whitelisted_channels', '[]'))
            
            if blacklist:
                blacklist_channels = []
                for channel_id in blacklist[:3]:  # Show first 3
                    channel = interaction.guild.get_channel(int(channel_id))
                    if channel:
                        blacklist_channels.append(channel.mention)
                blacklist_text = ", ".join(blacklist_channels)
                if len(blacklist) > 3:
                    blacklist_text += f" (+{len(blacklist) - 3} more)"
            else:
                blacklist_text = "None"
                
            embed.add_field(
                name="🚫 Blacklisted Channels",
                value=blacklist_text,
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(
                "An error occurred while fetching the configuration.", ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(LevelingCog(bot))