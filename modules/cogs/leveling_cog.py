import asyncio
import logging

import discord
from discord.ext import commands
from discord import app_commands
from modules.leveling_system import get_leveling_system
from typing import Optional


class LevelingCog(commands.Cog):
    """Commands and event handling for the leveling system."""

    def __init__(self, bot):
        self.bot = bot
        self.leveling_system = get_leveling_system(bot)
        bot.logger.info("LevelingCog initialized")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if not message.guild:
            return
        if not self.bot.start_time:
            return
        if message.created_at < self.bot.start_time:
            return
        if self.leveling_system:
            asyncio.create_task(self._process_xp_award(message))

    async def _process_xp_award(self, message: discord.Message):
        try:
            result = await self.leveling_system.process_message(message)
            if result and result.get('level_up'):
                await self._handle_level_up_announcement(message, result)
        except Exception as e:
            logging.error(f"Error processing XP award: {e}")

    async def _handle_level_up_announcement(self, message: discord.Message, level_result: dict):
        try:
            config = await self.leveling_system.get_guild_config(str(message.guild.id))

            if not config.get('level_up_announcements', True):
                return

            old_level = level_result['old_level']
            new_level = level_result['new_level']

            level_up_message = await self.leveling_system.get_level_up_message(
                str(message.author.id), str(message.guild.id), old_level, new_level
            )

            rank_info = await self.leveling_system.get_user_rank(str(message.author.id), str(message.guild.id))
            if rank_info and rank_info.get('rank_title'):
                level_up_message += f" ({rank_info['rank_title']})"

            announcement_channel_id = config.get('announcement_channel_id')
            if announcement_channel_id:
                try:
                    channel = self.bot.get_channel(int(announcement_channel_id))
                    if channel:
                        await channel.send(level_up_message)
                    else:
                        await message.channel.send(level_up_message)
                except Exception:
                    await message.channel.send(level_up_message)
            else:
                await message.channel.send(level_up_message)

            if config.get('dm_level_notifications', False):
                try:
                    await message.author.send(
                        f"\U0001f4e3 You leveled up in **{message.guild.name}**! You are now **Level {new_level}**!"
                    )
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Error handling level up announcement: {e}")

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
                        "You haven't earned any XP yet! Start chatting to begin leveling up! \U0001f3ae",
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

            xp_needed, progress = self.leveling_system.get_xp_for_next_level(current_level, current_xp)
            next_level_total_xp = self.leveling_system.get_xp_required_for_level(current_level + 1)

            rank_info = await self.leveling_system.get_user_rank(
                str(target_user.id), str(interaction.guild_id)
            )

            embed = discord.Embed(
                title=f"\U0001f4ca {target_user.display_name}'s Level Stats",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="\U0001f3c6 Current Level",
                value=f"**{current_level}**",
                inline=True
            )

            embed.add_field(
                name="\u2b50 Total XP",
                value=f"**{total_xp:,}**",
                inline=True
            )

            if rank_info and rank_info.get('server_rank'):
                embed.add_field(
                    name="\U0001f947 Server Rank",
                    value=f"**#{rank_info['server_rank']}**",
                    inline=True
                )

            embed.add_field(
                name="\U0001f4c8 Progress to Next Level",
                value=f"**{current_xp}/{next_level_total_xp - self.leveling_system.get_xp_required_for_level(current_level)}** XP\n"
                      f"({progress}% complete)\n"
                      f"*{xp_needed} XP remaining*",
                inline=False
            )

            embed.add_field(
                name="\U0001f4ac Messages Sent",
                value=f"**{messages_sent:,}**",
                inline=True
            )

            embed.add_field(
                name="\U0001f4c5 Daily XP Earned",
                value=f"**{user_data.get('daily_xp_earned', 0)}**",
                inline=True
            )

            if rank_info and rank_info.get('rank_title'):
                embed.add_field(
                    name="\U0001f396\ufe0f Current Rank",
                    value=f"**{rank_info['rank_title']}**",
                    inline=True
                )

            range_info = await self.leveling_system.get_user_range(
                str(target_user.id), str(interaction.guild_id)
            )
            if range_info:
                embed.add_field(
                    name="\U0001f3c5 Rank Tier",
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
        limit = min(max(limit, 1), 20)

        try:
            leaderboard = await self.leveling_system.get_leaderboard(
                str(interaction.guild_id), limit
            )

            if not leaderboard:
                await interaction.response.send_message(
                    "No one has earned XP yet! Be the first to start chatting! \U0001f3ae",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title=f"\U0001f3c6 {interaction.guild.name} Leaderboard",
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

                rank_info = await self.leveling_system.get_user_rank(
                    entry['user_id'], str(interaction.guild_id)
                )

                if i == 1:
                    medal = "\U0001f947"
                elif i == 2:
                    medal = "\U0001f948"
                elif i == 3:
                    medal = "\U0001f949"
                else:
                    medal = f"**{i}.**"

                rank_display = ""
                if rank_info and rank_info.get('rank_title'):
                    emoji_prefix = f"{rank_info.get('emoji', '')} " if rank_info.get('emoji') else ""
                    rank_display = f" \u2022 {emoji_prefix}{rank_info['rank_title']}"

                range_display = ""
                if entry.get('range_name'):
                    range_display = f" \u2022 \U0001f3c5 {entry['range_name']}"

                leaderboard_text.append(
                    f"{medal} {name}\n"
                    f"   Level {entry['current_level']} \u2022 {entry['total_xp']:,} XP{rank_display}{range_display}"
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
