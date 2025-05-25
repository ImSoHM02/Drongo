import discord
from discord import app_commands
from modules.ai.civitai.civitai_ai import generate_image
from modules.ai.civitai.civitai_prompts import DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT

def setup(bot):
    @bot.tree.command(name="civitai_generate", description="Generate an image using Civitai AI.")
    @app_commands.describe(
        prompt="The main prompt for the image generation.",
        model_urn="The Civitai model URN to use for generation."
    )
    async def civitai_generate(
        interaction: discord.Interaction,
        prompt: str,
        model_urn: str = ""
    ):
        await interaction.response.defer()
        response = generate_image(
            prompt=prompt,
            model_urn=model_urn if model_urn != "" else None
        )

        if "error" in response:
            await interaction.followup.send(f"Error generating image: {response['error']}")
        else:
            if response and 'url' in response:
                await interaction.followup.send(f"Image generated: {response['url']}")
            else:
                await interaction.followup.send(f"Image generation initiated. Response: {response}. Please check Civitai for the result.")
        
        bot.stats_display.update_stats("Commands Executed", bot.stats_display.stats["Commands Executed"] + 1)