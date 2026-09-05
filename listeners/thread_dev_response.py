import config
import discord
from discord.ext import commands

class ThreadDevResponse(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.Thread):
            return
        
        has_role = any(role.id in {config.roles["developer"], config.roles["dev_test"]} for role in message.author.roles)
        if not has_role:
            return

        tag = discord.utils.get(message.channel.parent.available_tags, name = "Developer Response")
        if not tag or tag in message.channel.applied_tags:
            return

        await message.channel.edit(applied_tags=[*message.channel.applied_tags, tag])

async def setup(bot: commands.Bot):
    await bot.add_cog(ThreadDevResponse(bot))