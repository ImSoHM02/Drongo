import discord
from discord import app_commands
from modules.ai.civitai.civitai_ai import generate_image
from modules.ai.civitai.civitai_prompts import DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT

class CivitaiAI(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="civitai_generate", description="Generate an image using Civitai AI.")
    async def civitai_generate(
        self,
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

def setup(bot):
    bot.add_cog(CivitaiAI(bot))