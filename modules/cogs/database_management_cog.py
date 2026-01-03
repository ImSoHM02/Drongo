import discord
from discord.ext import commands
from discord import app_commands
import os
from database_utils import optimized_db

class DatabaseManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    db = app_commands.Group(name="db", description="Database management commands")

    @db.command(name="health")
    async def database_health(self, interaction: discord.Interaction):
        """Check database health and performance metrics."""
        authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
        if str(interaction.user.id) != authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        
        try:
            health_info = await optimized_db.analyze_database_health()
            
            embed = discord.Embed(
                title="Database Health Report",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Database Size",
                value=f"{health_info['database_size_mb']} MB",
                inline=True
            )
            
            embed.add_field(
                name="Tables",
                value=str(health_info['table_count']),
                inline=True
            )
            
            embed.add_field(
                name="Indexes",
                value=str(health_info['index_count']),
                inline=True
            )
            
            if health_info.get('indexes'):
                embed.add_field(
                    name="Custom Indexes",
                    value="\n".join(health_info['indexes'][:10]),  # Limit to first 10
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"Error checking database health: {str(e)}")

    @db.command(name="flush")
    async def flush_batches(self, interaction: discord.Interaction):
        """Flush pending message batches to database."""
        authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
        if str(interaction.user.id) != authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return

        await interaction.response.defer()
        
        try:
            await optimized_db.flush_message_batch()
            await interaction.followup.send("Message batches flushed to database.")
            
        except Exception as e:
            await interaction.followup.send(f"Error flushing batches: {str(e)}")

    @db.command(name="stats")
    @app_commands.describe(user="User to get detailed stats for")
    async def database_stats(self, interaction: discord.Interaction, user: discord.Member = None):
        """Get database statistics."""
        authorized_user_id = os.getenv("AUTHORIZED_USER_ID")
        if str(interaction.user.id) != authorized_user_id:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
            return
            
        await interaction.response.defer()
        
        try:
            if user:
                # Get user-specific stats
                stats = await optimized_db.get_user_message_stats(str(user.id), str(interaction.guild.id))
                
                embed = discord.Embed(
                    title=f"Stats for {user.display_name}",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Total Messages",
                    value=f"{stats['total_messages']:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="Recent Messages (7 days)",
                    value=f"{stats['recent_messages']:,}",
                    inline=True
                )
                
                if stats['most_active_channel']:
                    channel = self.bot.get_channel(int(stats['most_active_channel']))
                    channel_name = channel.name if channel else "Unknown Channel"
                    embed.add_field(
                        name="Most Active Channel",
                        value=f"#{channel_name} ({stats['channel_message_count']:,} messages)",
                        inline=False
                    )
                
            else:
                # Get server-wide stats
                stats = await optimized_db.get_server_activity_summary(str(interaction.guild.id))
                
                embed = discord.Embed(
                    title=f"Server Stats for {interaction.guild.name}",
                    color=discord.Color.green()
                )
                
                embed.add_field(
                    name="Total Messages",
                    value=f"{stats['total_messages']:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="Unique Users",
                    value=f"{stats['unique_users']:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="Today's Messages",
                    value=f"{stats['today_messages']:,}",
                    inline=True
                )
                
                if stats['top_users']:
                    top_users_text = []
                    for i, (user_id, count) in enumerate(stats['top_users'][:5], 1):
                        try:
                            member = interaction.guild.get_member(int(user_id))
                            name = member.display_name if member else f"User {user_id}"
                            top_users_text.append(f"{i}. {name}: {count:,}")
                        except:
                            top_users_text.append(f"{i}. Unknown User: {count:,}")
                    
                    embed.add_field(
                        name="Top Users",
                        value="\n".join(top_users_text),
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"Error getting stats: {str(e)}")


async def setup(bot):
    await bot.add_cog(DatabaseManagementCog(bot))