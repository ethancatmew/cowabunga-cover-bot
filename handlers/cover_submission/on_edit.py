import config
import discord
from discord import ui
from discord.ext import commands

class EditModal(ui.Modal, title = "Edit Submission"):
    def __init__(self, bot: commands.Bot, source: str):
        super().__init__()
        self.bot = bot

        top, code = source.split("\n", 1)
        self.top = top
        self.code = code

        self.edit = ui.TextInput(
            label = "Module Code",
            required = True,
            style = discord.TextStyle.paragraph,
            default = self.code
        )
        self.add_item(self.edit)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content = f"{self.top}\n{self.edit.value}")

async def edit(bot: commands.Bot, interaction: discord.Interaction):
    has_role = any(role.id in {config.roles["developer"], config.roles["dev_test"]} for role in interaction.user.roles)
    if not has_role:
        return await interaction.response.send_message("**ERROR**:warning: You do not have permission to edit covers.", ephemeral = True)

    source = interaction.message.content
    await interaction.response.send_modal(EditModal(bot, source))