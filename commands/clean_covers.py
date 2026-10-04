import config
import discord
from discord import app_commands
from discord.ext import commands

class CleanCovers(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name = "clean_covers", description = "Removes all the covers sent in by users who left the server")
    @app_commands.checks.has_any_role(config.roles["developer"], config.roles["dev_test"])
    async def clean(self, interaction: discord.Interaction):
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