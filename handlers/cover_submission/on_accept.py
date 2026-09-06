import config
import discord
from discord.ext import commands

async def approve(bot: commands.Bot, interaction: discord.Interaction, title_artist: str):
    has_role = any(role.id in {config.roles["developer"], config.roles["dev_test"], config.roles["cover_reviewer"]} for role in interaction.user.roles)
    if not has_role:
        return await interaction.response.send_message("**ERROR**:warning: You do not have permission to accept covers.", ephemeral = True)

    submitter_id = int(interaction.message.content.splitlines()[0])
    user = await bot.fetch_user(submitter_id)
    if not user:
        await interaction.response.send_message("**ERROR**:warning: Failed to find user.", ephemeral = True)
        return

    try:
        await user.send(f"Your cover of **{title_artist}** has been accepted! You can find the song in-game shortly. If this is your first accepted cover, you can find some cover artist rewards in your inventory!")
    except discord.Forbidden:
        await interaction.response.send_message("Submitter has DMs disabled.", ephemeral = True)
        return

    await interaction.message.delete()