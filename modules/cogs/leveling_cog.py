import discord
import os
from datetime import datetime
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

    @level.command(name="config")
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
            from database_modules.database_pool import get_leveling_pool
            pool = await get_leveling_pool()
            
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
            guild_id = str(interaction.guild_id)
            if hasattr(self.leveling_system, 'clear_guild_config_cache'):
                self.leveling_system.clear_guild_config_cache(guild_id)
            
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

    @level.command(name="view-config")
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
    @level.command(name="addlevel")
    @app_commands.describe(
        user="The user to add levels to",
        levels="The number of levels to add"
    )
    async def add_level(self, interaction: discord.Interaction, user: discord.User, levels: int):
        """Add levels to a user for testing purposes."""
        await interaction.response.defer(ephemeral=True)
        authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
        if str(interaction.user.id) != authorized_user_id:
            await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)
            return

        user_data = await self.leveling_system.get_user_level_data(str(user.id), str(interaction.guild_id))
        if not user_data:
            current_level = 0
            total_xp = 0
        else:
            current_level = user_data['current_level']
            total_xp = user_data['total_xp']

        new_level = current_level + levels
        required_xp = self.leveling_system.get_xp_required_for_level(new_level)
        xp_to_add = required_xp - total_xp

        if xp_to_add > 0:
            from database_modules.database_pool import get_leveling_pool
            pool = await get_leveling_pool()
            await pool.execute_write(
                "UPDATE user_levels SET total_xp = ?, current_xp = ? WHERE user_id = ? AND guild_id = ?",
                (required_xp, required_xp - self.leveling_system.get_xp_required_for_level(new_level), str(user.id), str(interaction.guild_id))
            )
            level_up_result = await self.leveling_system.check_level_up(str(user.id), str(interaction.guild_id))
            if level_up_result and level_up_result.get('level_up'):
                # Manually trigger announcement
                level_up_message = await self.leveling_system.get_level_up_message(
                    str(user.id), str(interaction.guild.id), level_up_result['old_level'], level_up_result['new_level']
                )
                await interaction.channel.send(level_up_message)

        await interaction.followup.send(f"Added {levels} levels to {user.mention}. They are now level {new_level}.", ephemeral=True)

    @level.command(name="addxp")
    @app_commands.describe(
        user="The user to award XP to",
        xp="The amount of XP to add"
    )
    async def add_xp(self, interaction: discord.Interaction, user: discord.User, xp: int):
        """Add raw XP to a user, triggering level ups if thresholds are crossed."""
        await interaction.response.defer(ephemeral=True)
        authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
        if str(interaction.user.id) != authorized_user_id:
            await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)
            return

        if xp <= 0:
            await interaction.followup.send("XP must be a positive value.", ephemeral=True)
            return

        from database_modules.database_pool import get_leveling_pool

        user_id = str(user.id)
        guild_id = str(interaction.guild_id)
        today = datetime.utcnow().date().isoformat()

        # Fetch current user data for calculations
        user_data = await self.leveling_system.get_user_level_data(user_id, guild_id)

        if user_data and user_data.get('daily_reset_date') == today:
            new_daily = user_data.get('daily_xp_earned', 0) + xp
        else:
            new_daily = xp

        pool = await get_leveling_pool()

        if user_data:
            await pool.execute_write(
                """
                UPDATE user_levels
                SET total_xp = total_xp + ?,
                    current_xp = current_xp + ?,
                    daily_xp_earned = ?,
                    daily_reset_date = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
                """,
                (xp, xp, new_daily, today, user_id, guild_id)
            )
        else:
            await pool.execute_write(
                """
                INSERT INTO user_levels (user_id, guild_id, current_xp, current_level, total_xp, messages_sent, daily_xp_earned, daily_reset_date)
                VALUES (?, ?, ?, 0, ?, 0, ?, ?)
                """,
                (user_id, guild_id, xp, xp, new_daily, today)
            )

        # Log manual transaction
        await pool.execute_write(
            """
            INSERT INTO xp_transactions (user_id, guild_id, channel_id, xp_awarded, reason, message_length, word_count, char_count, daily_cap_applied)
            VALUES (?, ?, 'MANUAL', ?, 'manual_add_xp', 0, 0, 0, 0)
            """,
            (user_id, guild_id, xp)
        )

        # Clear cached user data so fresh values are returned
        cache_key = f"{user_id}:{guild_id}"
        self.leveling_system._user_cache.pop(cache_key, None)
        self.leveling_system._user_cache_expiry.pop(cache_key, None)

        # Recalculate level after XP change
        level_up_result = await self.leveling_system.check_level_up(user_id, guild_id)
        updated_data = await self.leveling_system.get_user_level_data(user_id, guild_id)

        # Notify channel if level up occurred
        if level_up_result and level_up_result.get('level_up'):
            level_up_message = await self.leveling_system.get_level_up_message(
                user_id, guild_id, level_up_result['old_level'], level_up_result['new_level']
            )
            await interaction.channel.send(level_up_message)

        total_xp = updated_data['total_xp'] if updated_data else xp
        current_level = updated_data['current_level'] if updated_data else self.leveling_system.calculate_level_from_xp(total_xp)

        await interaction.followup.send(
            f"Added {xp} XP to {user.mention}. They now have **{total_xp:,}** XP and are level **{current_level}**.",
            ephemeral=True
        )

    @level.command(name="removelevel")
    @app_commands.describe(
        user="The user to remove levels from",
        levels="The number of levels to remove"
    )
    async def remove_level(self, interaction: discord.Interaction, user: discord.User, levels: int):
        """Remove levels from a user for testing purposes."""
        await interaction.response.defer(ephemeral=True)
        authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
        if str(interaction.user.id) != authorized_user_id:
            await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)
            return

        user_data = await self.leveling_system.get_user_level_data(str(user.id), str(interaction.guild_id))
        if not user_data:
            await interaction.followup.send(f"{user.mention} has no levels to remove.", ephemeral=True)
            return

        current_level = user_data['current_level']
        new_level = max(0, current_level - levels)
        required_xp = self.leveling_system.get_xp_required_for_level(new_level)

        from database_modules.database_pool import get_leveling_pool
        pool = await get_leveling_pool()
        await pool.execute_write(
            "UPDATE user_levels SET total_xp = ?, current_xp = 0, current_level = ? WHERE user_id = ? AND guild_id = ?",
            (required_xp, new_level, str(user.id), str(interaction.guild_id))
        )

        await interaction.followup.send(f"Removed {levels} levels from {user.mention}. They are now level {new_level}.", ephemeral=True)
async def setup(bot):
    bot.logger.info("Setting up LevelingCog...")
    await bot.add_cog(LevelingCog(bot))
    bot.logger.info("LevelingCog added successfully")
