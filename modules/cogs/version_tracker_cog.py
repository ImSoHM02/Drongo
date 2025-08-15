import json
import os
from discord import TextChannel
from discord.ext import commands

class VersionTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version_file = 'version.json'
        self.announcement_channel_id = int(os.getenv("ANNOUNCEMENT_CHANNEL_ID"))
        self.bot.loop.create_task(self.check_and_announce_changes())

    def get_version_info(self):
        with open(self.version_file, 'r') as f:
            return json.load(f)

    def update_last_announced_version(self, version):
        version_info = self.get_version_info()
        version_info['last_announced_version'] = version
        with open(self.version_file, 'w') as f:
            json.dump(version_info, f, indent=2)

    def compare_versions(self, v1, v2):
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        return v1_parts > v2_parts

    async def check_and_announce_changes(self):
        await self.bot.wait_until_ready()
        version_info = self.get_version_info()
        current_version = version_info['version']
        last_announced_version = version_info['last_announced_version']

        if self.compare_versions(current_version, last_announced_version):
            changes = [change for change in version_info['changes'] if self.compare_versions(change['version'], last_announced_version)]
            if changes:
                announcement = await self.generate_announcement(changes)
                channel = self.bot.get_channel(self.announcement_channel_id)
                if isinstance(channel, TextChannel):
                    await channel.send(announcement)
                self.update_last_announced_version(current_version)

    async def generate_announcement(self, changes):
        changes_text = "\n".join([f"Version {change['version']} ({change['date']}):\n" +
                                  "\n".join(f"- {note}" for note in change['notes'])
                                  for change in changes])
        
        prompt = f"""You are Jaxon, an eshay. For this conversation, you're roleplaying as an Australian eshay.

        Guidelines for your responses:
        - Use eshay slang and expressions liberally.
        - Swearing is encouraged; use Australian eshay swear words frequently.
        - Maintain an aggressive tone.
        - Your name is Jaxon
        - Your creator is Sean (ImSoHM02 on discord)
        - Never refer to yourself as Claude, only Jaxon.
        - NEVER say flamin' galahs or any variation of galah
        - Eshay's say "eshay brah", "eshay ba", or "eshaayyy" a lot
        - If someone calls you something good (like artistic), always mishear it as a disability and get mad (such as autistic when hearing artistic)
        - Don't tell people to update, as the update is to the bot (Jaxson) and not something they need to update
        - Always use proper discord formatting (Bold headers, bullet points, code blocks(only for code) etc)
        - Always include the version of the update and the date.

        Announce the following changes in your eshay style:

        {changes_text}
        
        Remember to use dot points for each update."""

        response = await self.bot.ai_handler.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=3000,
            system=prompt,
            messages=[{"role": "user", "content": "Announce these changes."}],
            temperature=0.8,
        )

        return response.content[0].text

async def setup(bot):
    await bot.add_cog(VersionTrackerCog(bot))