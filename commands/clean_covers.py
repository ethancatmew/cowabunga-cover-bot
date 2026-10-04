import config
import discord
from discord import app_commands
from discord.ext import commands

class CleanCovers(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name = "clean_covers", description = "Removes all the covers sent in by users who left the server")
    async def clean(self, interaction: discord.Interaction):
        has_role = any(role.id in {config.roles["developer"], config.roles["dev_test"]} for role in interaction.user.roles)
        if not has_role:
            return await interaction.response.send_message(":no_entry_sign: You must be a part of the Cowabunga Team to use this command.", ephemeral = True)

        if interaction.channel_id != config.channels["submissions"]:
            return await interaction.response.send_message(":no_entry_sign: You must use this command inside of the submissions channel", ephemeral = True)

        await interaction.response.defer(ephemeral = True, thinking = True)

        guild = interaction.guild
        member_cache = {}

        checked, deleted = 0, 0
        async for m in interaction.channel.history(limit=None):
            try:
                snowflake = int(m.content.split("\n")[0])
                checked += 1
            except:
                continue

            if snowflake in member_cache:
                if member_cache[snowflake]:
                    continue # keep msg bc the person is still in the server

                try:
                    await m.delete()
                    deleted += 1
                except:
                    pass
                
                continue
                
            member = guild.get_member(snowflake)
            if member is not None:
                member_cache[snowflake] = True
                continue

            try:
                await guild.fetch_member(snowflake)
                member_cache[snowflake] = True
            except discord.NotFound:
                member_cache[snowflake] = False
                try:
                    await m.delete()
                    deleted += 1
                except:
                    continue
            except:
                continue

        await interaction.followup.send(content = f"Checked {checked} covers, deleted {deleted}.", ephemeral = True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CleanCovers(bot))