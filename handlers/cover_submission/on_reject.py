import config
import discord
from discord import ui
from discord.ext import commands

class FeedbackModal(ui.Modal, title = "Cover Declined Feedback"):
    def __init__(self, bot: commands.Bot, submitter_id: int):
        super().__init__()
        self.bot = bot
        self.submitter_id = submitter_id


    feedback = ui.TextInput(
        label = "Enter Feedback",
        placeholder = "Optional feedback...",
        required = False,
        style = discord.TextStyle.long
    )

    async def on_submit(self, interaction: discord.Interaction):
        reviewer = interaction.user
        submitter = await self.bot.fetch_user(self.submitter_id)

        if not submitter:
            await interaction.response.send_message("Cannot find the submitter.")

        # TODO: make it so it says the song name vv
        BASE_DECLINED = f"We appreciate your submission of **{None}** to the game. This time, we couldn't accept it."
        BASE_REASONS = "**Please make sure your cover has all of the following:**\n> Clear and audible vocals\n> Correct melody\n> Correct lyrics\n> No background noise\n> No added voice effects\n> Is NOT on [this list](https://pastebin.com/rpYgpesT)"

        msg = BASE_DECLINED
        if len(self.feedback.value) > 0:
            msg += f'\n\nThe following feedback was left by the person who reviewed your cover:\n```{self.feedback.value}\n```'
        else:
            msg += f'\n\n{BASE_REASONS}'

        try:
            submitter.send(msg)
            await interaction.response.send_message("Feedback submitted.", ephemeral = True)
        except discord.Forbidden:
            await interaction.response.send_message("**ERROR**:warning: Submitter has DMs disabled.", ephemeral = True)

        if len(self.feedback.value > 0):
            feedback_log_channel = self.bot.get_channel(config.channels["feedback_log"])
            if feedback_log_channel:
                await feedback_log_channel.send(f"{reviewer.mention}: {self.note.value}")

        await interaction.message.delete()


def reject(bot: commands.Bot, interaction: discord.Interaction):
    submitter_id = int(interaction.message.content)

