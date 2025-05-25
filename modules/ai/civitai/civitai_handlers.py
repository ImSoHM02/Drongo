import discord
from discord.commands import SlashCommandGroup
from modules.ai.civitai.civitai_ai import generate_image
from modules.ai.civitai.civitai_prompts import DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT

class CivitaiAI(discord.Cog):
    def __init__(self, bot):
        self.bot = bot

    civitai_commands = SlashCommandGroup("civitai", "Commands for Civitai AI image generation.")

    @civitai_commands.command(name="generate", description="Generate an image using Civitai AI.")
    async def generate(
        self,
        ctx: discord.ApplicationContext,
        prompt: str = discord.Option(str, description="The main prompt for the image generation.", default=DEFAULT_PROMPT),
        negative_prompt: str = discord.Option(str, description="The negative prompt for the image generation.", default=DEFAULT_NEGATIVE_PROMPT),
        width: int = discord.Option(int, description="The width of the generated image.", default=512),
        height: int = discord.Option(int, description="The height of the generated image.", default=512),
        steps: int = discord.Option(int, description="The number of steps for the image generation process.", default=20),
        cfg_scale: int = discord.Option(int, description="The CFG scale for the image generation.", default=7),
        model_urn: str = discord.Option(str, description="The Civitai model URN to use for generation.", default="")
    ):
        await ctx.defer()
        response = generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            steps=steps,
            cfg_scale=cfg_scale,
            model_urn=model_urn if model_urn != "" else None # Use default from civitai_ai if empty string
        )

        if "error" in response:
            await ctx.followup.send(f"Error generating image: {response['error']}")
        else:
            # Assuming the response contains a URL to the generated image
            # You might need to inspect the actual response structure from civitai.image.create
            # For now, let's assume it returns a direct URL or a job ID to fetch the image later.
            # The documentation shows `response = civitai.image.create(input)` and doesn't specify the return type.
            # I'll assume it returns a dictionary with a 'url' key for the image.
            # If it returns a job ID, I'll need to implement a polling mechanism or a callback.
            # For simplicity, I'll assume a direct URL for now.
            # TODO: Verify the actual response structure and handle image retrieval.
            if response and 'url' in response:
                await ctx.followup.send(f"Image generated: {response['url']}")
            else:
                await ctx.followup.send(f"Image generation initiated. Response: {response}. Please check Civitai for the result.")

def setup(bot):
    bot.add_cog(CivitaiAI(bot))