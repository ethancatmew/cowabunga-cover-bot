import config
import discord
from discord import ui
from discord.ext import commands

class FeedbackModal(ui.Modal, title = "Cover Declined Feedback"):
    def __init__(self, bot: commands.Bot, submitter_id: int, title_artist: str):
        super().__init__()
        self.bot = bot
        self.submitter_id = submitter_id
        self.title_artist = title_artist


    feedback = ui.TextInput(
        label = "Enter Feedback",
        placeholder = "Optional feedback...",
        required = False,
        style = discord.TextStyle.long
    )

    async def on_submit(self, interaction: discord.Interaction):
        reviewer = interaction.user
        feedback = self.feedback.value.strip()

        try:
            submitter = await self.bot.fetch_user(self.submitter_id)
        except discord.NotFound:
            await interaction.response.send_message("Cannot find the submitter.", ephemeral = True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("Could not retrieve the submitter. Please try again.", ephemeral = True)
            return

        BASE_DECLINED = (
            f"We appreciate your submission of **{self.title_artist}** to the game. "
            "This time, we couldn't accept it."
        )
        BASE_REASONS = (
            "**Please make sure your cover has all of the following:**\n"
            "> Clear and audible vocals\n"
            "> Correct melody\n"
            "> Correct lyrics\n"
            "> No background noise\n"
            "> No added voice effects\n"
            "> Is NOT on [this list](https://pastebin.com/rpYgpesT)"
        )

        msg = BASE_DECLINED
        if feedback:
            safe_feedback = feedback.replace("```", "'''")
            msg += f'\n\nThe following feedback was left by the person who reviewed your cover:\n```text\n{safe_feedback}\n```'
        else:
            msg += f'\n\n{BASE_REASONS}'

        if len(msg) > 2000:
            msg = msg[:1997] + "..."

        try:
            await submitter.send(msg)
            await interaction.response.send_message("Feedback submitted.", ephemeral = True)
        except discord.Forbidden:
            await interaction.response.send_message("**ERROR**:warning: Submitter has DMs disabled.", ephemeral = True)
            return
        except discord.HTTPException:
            await interaction.response.send_message("**ERROR**:warning: Could not send the rejection message.", ephemeral = True)
            return

        if feedback:
            feedback_log_channel = self.bot.get_channel(config.channels["feedback_log"])
            if feedback_log_channel:
                log_message = f"{reviewer.mention} to {submitter.mention}: {feedback}"
                if len(log_message) > 2000:
                    log_message = log_message[:1997] + "..."
                try:
                    await feedback_log_channel.send(log_message)
                except (discord.Forbidden, discord.HTTPException):
                    pass

        try:
            await interaction.message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass

async def reject(bot: commands.Bot, interaction: discord.Interaction, title_artist: str):
    has_role = any(role.id in {config.roles["developer"], config.roles["dev_test"], config.roles["cover_reviewer"]} for role in interaction.user.roles)
    if not has_role:
        return await interaction.response.send_message("**ERROR**:warning: You do not have permission to deny covers.", ephemeral = True)

    submitter_id = int(interaction.message.content.splitlines()[0])
    await interaction.response.send_modal(FeedbackModal(bot, submitter_id, title_artist))