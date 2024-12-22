from discord.ext import commands
import discord
import random

def setup(bot):
    pranked_users = {}  # Keep track of users who have been pranked
    
    @bot.event
    async def on_message(message):
        # Don't respond to bots, including ourselves
        if message.author.bot:
            return
            
        try:
            # Check if this user was previously pranked
            if message.author.id in pranked_users:
                await message.reply("get fuckin' pranked cunt")
                del pranked_users[message.author.id]
                return

            # 1% chance to react
            if random.random() < 0.05:
                try:
                    pika_emoji = discord.utils.get(message.guild.emojis, name='pikaThumbsUp')
                    if pika_emoji:
                        await message.add_reaction(pika_emoji)
                        pranked_users[message.author.id] = True
                except discord.errors.Forbidden:
                    pass  # Silently fail if we don't have permission to react
                    
            # Make sure other commands still work
            await bot.process_commands(message)
            
        except Exception as e:
            if hasattr(bot, 'logger'):
                bot.logger.error(f"Error in prank module: {str(e)}")