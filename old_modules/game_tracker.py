# modules/game_tracker.py

import aiohttp
import discord
import logging
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import tasks
from database import get_db_connection, add_game_tracker, remove_game_tracker, get_user_tracked_games, update_game_price


async def get_game_price(app_id):
    async with aiohttp.ClientSession() as session:
        # Fetch USD price
        async with session.get(f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=us&filters=price_overview") as response:
            usd_data = await response.json()
        
        # Fetch AUD price
        async with session.get(f"https://store.steampowered.com/api/appdetails?appids={app_id}&cc=au&filters=price_overview") as response:
            aud_data = await response.json()
        
        if usd_data and aud_data and str(app_id) in usd_data and str(app_id) in aud_data:
            usd_price_info = usd_data[str(app_id)]["data"].get("price_overview")
            aud_price_info = aud_data[str(app_id)]["data"].get("price_overview")
            
            if usd_price_info and aud_price_info:
                return {
                    "current_price_usd": usd_price_info["final"] / 100,
                    "original_price_usd": usd_price_info["initial"] / 100,
                    "current_price_aud": aud_price_info["final"] / 100,
                    "original_price_aud": aud_price_info["initial"] / 100,
                    "discount_percent": usd_price_info["discount_percent"]
                }
    return None

async def search_steam_game(game_name):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://store.steampowered.com/api/storesearch?term={game_name}&l=english&cc=US") as response:
            data = await response.json()
            if data['total'] > 0:
                return data['items'][0]['id'], data['items'][0]['name']
            return None, None

async def track_game(interaction: discord.Interaction, game_name: str):
    await interaction.response.defer()
    app_id, exact_name = await search_steam_game(game_name)
    if app_id is None:
        await interaction.followup.send(f"Couldn't find a game matching '{game_name}' on Steam.")
        return

    price_info = await get_game_price(app_id)

    conn = await get_db_connection()
    try:
        if price_info:
            current_price_usd = price_info["current_price_usd"]
            current_price_aud = price_info["current_price_aud"]
            await add_game_tracker(conn, str(interaction.user.id), exact_name, app_id, current_price_usd)
            
            if price_info["discount_percent"] > 0:
                response = (f"Now tracking {exact_name} (AppID: {app_id}).\n"
                            f"This game is currently on sale!\n"
                            f"Original price: ${price_info['original_price_usd']:.2f} (A${price_info['original_price_aud']:.2f})\n"
                            f"Current price: ${current_price_usd:.2f} (A${current_price_aud:.2f})\n"
                            f"Discount: {price_info['discount_percent']}% off")
            else:
                response = f"Now tracking {exact_name} (AppID: {app_id}, Current Price: ${current_price_usd:.2f} (A${current_price_aud:.2f})) for you."
        else:
            await add_game_tracker(conn, str(interaction.user.id), exact_name, app_id, None)
            response = f"Now tracking {exact_name} (AppID: {app_id}, Current Price: Unknown) for you."
        
        await interaction.followup.send(response)
    except Exception as e:
        await interaction.followup.send(f"Error tracking game: {str(e)}", ephemeral=True)
    finally:
        await conn.close()

async def untrack_game(interaction: discord.Interaction, game_name: str):
    conn = await get_db_connection()
    try:
        await remove_game_tracker(conn, str(interaction.user.id), game_name)
        await interaction.response.send_message(f"Stopped tracking {game_name} for you.")
    except Exception as e:
        await interaction.response.send_message(f"Error untracking game: {str(e)}", ephemeral=True)
    finally:
        await conn.close()

async def list_tracked_games(interaction: discord.Interaction):
    conn = await get_db_connection()
    try:
        games = await get_user_tracked_games(conn, str(interaction.user.id))
        if games:
            game_list = []
            for game in games:
                game_name, app_id, current_price_usd, last_checked = game
                price_info = await get_game_price(app_id)
                if price_info:
                    price_str = f"${price_info['current_price_usd']:.2f} (A${price_info['current_price_aud']:.2f})"
                else:
                    price_str = "Unknown"
                game_list.append(f"{game_name} (AppID: {app_id}, Current Price: {price_str})")
            
            await interaction.response.send_message(f"Your tracked games:\n" + "\n".join(game_list))
        else:
            await interaction.response.send_message("You are not tracking any games.")
    except Exception as e:
        await interaction.response.send_message(f"Error listing tracked games: {str(e)}", ephemeral=True)
    finally:
        await conn.close()
        
@tasks.loop(hours=4)
async def check_game_deals(bot):
    conn = await get_db_connection()
    try:
        async with conn.execute("SELECT DISTINCT app_id FROM game_trackers WHERE app_id IS NOT NULL") as cursor:
            games = await cursor.fetchall()
        
        for (app_id,) in games:
            price_info = await get_game_price(app_id)
            if price_info:
                current_price_usd = price_info["current_price_usd"]
                current_price_aud = price_info["current_price_aud"]
                discount_percent = price_info["discount_percent"]
                
                if discount_percent > 0:
                    async with conn.execute("""
                        SELECT DISTINCT user_id, game_name, last_notified 
                        FROM game_trackers 
                        WHERE app_id = ?
                    """, (app_id,)) as cursor:
                        users = await cursor.fetchall()
                    
                    for user_id, game_name, last_notified in users:
                        # Check if we've notified about this deal in the last 30 days
                        if last_notified is None or (datetime.now() - datetime.fromisoformat(last_notified)) > timedelta(days=30):
                            user = await bot.fetch_user(int(user_id))
                            await user.send(f"Deal alert! {game_name} is now {discount_percent}% off on Steam. "
                                            f"Current price: ${current_price_usd:.2f} (A${current_price_aud:.2f})")
                            await update_game_price(conn, app_id, current_price_usd, notified=True)
                        else:
                            # Update the price without updating the notification time
                            await update_game_price(conn, app_id, current_price_usd, notified=False)
                else:
                    # If there's no discount, just update the price
                    await update_game_price(conn, app_id, current_price_usd, notified=False)
    except Exception as e:
        logging.error(f"Error checking game deals: {str(e)}")
    finally:
        await conn.close()

def setup(bot):
    @bot.tree.command(name="track_game")
    @app_commands.describe(game_name="The name of the game to track")
    async def track_game_command(interaction: discord.Interaction, game_name: str):
        await track_game(interaction, game_name)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(name="untrack_game")
    @app_commands.describe(game_name="The name of the game to stop tracking")
    async def untrack_game_command(interaction: discord.Interaction, game_name: str):
        await untrack_game(interaction, game_name)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    @bot.tree.command(name="list_tracked_games")
    async def list_tracked_games_command(interaction: discord.Interaction):
        await list_tracked_games(interaction)
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)

    # Start the game deal checker
    check_game_deals.start(bot)
    logging.info("Game deal checker started.")