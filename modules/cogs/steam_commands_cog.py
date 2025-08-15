import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

class SteamAPI:
    def __init__(self):
        with open('id.env') as f:
            for line in f:
                if line.startswith('STEAM_API_KEY='):
                    self.api_key = line.split('=')[1].strip()
                    break
            else:
                raise ValueError("STEAM_API_KEY not found in id.env")
        self._cache: Dict[str, Tuple[List[dict], datetime]] = {}
        self._cache_duration = timedelta(hours=24)

    def _get_cached_achievements(self, app_id: str) -> Optional[List[dict]]:
        if app_id in self._cache:
            achievements, timestamp = self._cache[app_id]
            if datetime.now() - timestamp < self._cache_duration:
                return achievements
            else:
                del self._cache[app_id]
        return None

    def _cache_achievements(self, app_id: str, achievements: List[dict]):
        self._cache[app_id] = (achievements, datetime.now())

    async def get_app_id(self, session: aiohttp.ClientSession, game_name: str) -> Optional[str]:
        url = f"https://api.steampowered.com/ISteamApps/GetAppList/v2/"
        async with session.get(url) as response:
            if response.status != 200:
                return None
            data = await response.json()
            apps = data['applist']['apps']
            for app in apps:
                if app['name'].lower() == game_name.lower():
                    return str(app['appid'])
        return None

    async def get_achievements(self, session: aiohttp.ClientSession, game_identifier: str) -> Tuple[bool, Optional[List[dict]], str]:
        app_id = game_identifier if game_identifier.isdigit() else await self.get_app_id(session, game_identifier)
        if not app_id:
            return False, None, "Game not found on Steam"
        cached = self._get_cached_achievements(app_id)
        if cached is not None:
            return True, cached, ""
        url = f"https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/?gameid={app_id}"
        async with session.get(url) as response:
            if response.status != 200:
                return False, None, "Failed to fetch achievements"
            data = await response.json()
            achievements = data.get('achievementpercentages', {}).get('achievements', [])
            if not achievements:
                return False, None, "No achievements found for this game"
            schema_url = f"https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key={self.api_key}&appid={app_id}"
            async with session.get(schema_url) as schema_response:
                if schema_response.status != 200:
                    return False, None, "Failed to fetch achievement details"
                schema_data = await schema_response.json()
                achievement_schema = schema_data.get('game', {}).get('availableGameStats', {}).get('achievements', [])
                combined_achievements = []
                for ach in achievement_schema:
                    for pct in achievements:
                        if ach['name'] == pct['name']:
                            combined_achievements.append({
                                'name': ach.get('displayName', ach['name']),
                                'description': ach.get('description', 'No description available'),
                                'icon': ach.get('icon', ''),
                                'percent': pct['percent']
                            })
                            break
                self._cache_achievements(app_id, combined_achievements)
                return True, combined_achievements, ""

class SteamCommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.steam_api = SteamAPI()
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    @app_commands.command(name="sra")
    @app_commands.describe(game="The name or App ID of the Steam game")
    async def random_achievement(self, interaction: discord.Interaction, game: str):
        """Get a random Steam achievement"""
        await interaction.response.defer()
        try:
            success, achievements, error = await self.steam_api.get_achievements(self.session, game)
            if not success:
                await interaction.followup.send(f"Error: {error}")
                return
            achievement = random.choice(achievements)
            embed = discord.Embed(
                title=f"Random Achievement from {game}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name=achievement['name'],
                value=achievement['description'],
                inline=False
            )
            embed.add_field(
                name="Global Unlock Rate",
                value=f"{float(achievement['percent']):.1f}%",
                inline=True
            )
            if achievement['icon']:
                embed.set_thumbnail(url=achievement['icon'])
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}")
        self.bot.stats_display.update_stats("Commands Executed", self.bot.stats_display.stats["Commands Executed"] + 1)

async def setup(bot):
    await bot.add_cog(SteamCommandsCog(bot))