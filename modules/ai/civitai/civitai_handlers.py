import discord
from discord.commands import SlashCommandGroup
from modules.ai.civitai.civitai_ai import generate_image
from modules.ai.civitai.civitai_prompts import DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT

class CivitaiAI(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.commands.slash_command(name="civitai_generate", description="Generate an image using Civitai AI.")
    async def civitai_generate(
        self,
        ctx: discord.ApplicationContext,
        prompt: str = discord.Option(str, description="The main prompt for the image generation.", required=True),
        model_urn: str = discord.Option(str, description="The Civitai model URN to use for generation.", default="")
    ):
        await ctx.defer()
        response = generate_image(
            prompt=prompt,
            model_urn=model_urn if model_urn != "" else None
        )

        if "error" in response:
            await ctx.followup.send(f"Error generating image: {response['error']}")
        else:
            if response and 'url' in response:
                await ctx.followup.send(f"Image generated: {response['url']}")
            else:
                await ctx.followup.send(f"Image generation initiated. Response: {response}. Please check Civitai for the result.")

def setup(bot):
    bot.add_cog(CivitaiAI(bot))