import config
import discord
import aiosqlite
from typing import Optional
from discord import app_commands
from discord.ext import commands

class CoverHelperCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name = "post_cover_button",
        description = "Post the cover submission text wall/button"
    )
    @app_commands.checks.has_any_role(config.roles["developer"], config.roles["dev_test"])
    async def post_cover_button(self, interaction: discord.Interaction):
        from commands.cover_submission import CoverSubmissionButton
        await interaction.response.send_message("Posted cover button!", ephemeral=True)
        await interaction.channel.send(content = config.cover_rules, view = CoverSubmissionButton(self.bot))

    @post_cover_button.error
    async def post_cover_button_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(":no_entry_sign: You must be a part of the Cowabunga Team to use this command.", ephemeral = True)


    @app_commands.command(
        name = "post_covers_disabled",
        description = "Post the covers disabled message with an optional reason"
    )
    @app_commands.checks.has_any_role(config.roles["developer"], config.roles["dev_test"])
    async def post_covers_disabled(self, interaction: discord.Interaction, reason: Optional[str]):
        base_msg = "# Cover Submissions\nUnfortunately, you caught us at a bad time! We're currently not accepting any submissions. Check back occasionally to see if submissions are back up."

        if reason is not None:
            base_msg += f"\n\nThe following reason was provided by {interaction.user.mention}:\n```\n{reason}\n```"
        
        await interaction.channel.send(content=base_msg)
        await interaction.response.send_message("Posted cover disabled message!", ephemeral = True)

    @post_covers_disabled.error
    async def post_covers_disabled_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(":no_entry_sign: You must be a part of the Cowabunga Team to use this command.", ephemeral = True)

    
    @app_commands.command(
        name = "clear_cooldown", 
        description = "Clear cover submission cooldown for a specific user."
    )
    @app_commands.checks.has_any_role(config.roles["developer"], config.roles["dev_test"])
    async def clear_cooldown(self, interaction: discord.Interaction, member: discord.Member):
        async with aiosqlite.connect(config.database) as database:
            await database.execute("DELETE FROM cooldowns WHERE user_id = ?", (member.id,))
            await database.commit()
        await interaction.response.send_message(f"Cleared cover submission cooldown for {member.mention}.", ephemeral = True)

    @clear_cooldown.error
    async def clear_cooldown_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(":no_entry_sign: You must be a part of the Cowabunga Team to use this command.", ephemeral = True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CoverHelperCommands(bot))