import config
import aiosqlite
import time
import math
import io
import mutagen
import discord
import requests
from typing import Optional
from discord import app_commands, ui
from discord.ext import commands, tasks

def not_cover_banned(user: discord.Member) -> bool:
    return not any(role.id == config.roles["cover_banned"] for role in user.roles)

class FeedbackModal(ui.Modal, title = "Cover Declined Feedback"):
    def __init__(self, bot: commands.Bot, submitter_id: int, title_artist: str):
        super().__init__()
        self.bot = bot
        self.submitter_id = submitter_id
        self.title_artist = title_artist

    note = ui.TextInput(label = "Feedback", placeholder = "Optional", required = False, style = discord.TextStyle.long)        
    
    async def on_submit(self, interaction: discord.Interaction):
        reviewer = interaction.user
        user = await self.bot.fetch_user(self.submitter_id)

        if not user:
            await interaction.response.send_message("Cannot find user.", ephemeral = True)
        
        BASE_DECLINED = f"We appreciate your submission of **{self.title_artist}** to the game. This time, we couldn't accept it."
        BASE_REASONS = "**Please make sure your cover has all of the following:**\n> Clear and audible vocals\n> Correct melody\n> Correct lyrics\n> No background noise\n> No added voice effects\n> Is NOT on [this list](https://pastebin.com/rpYgpesT)"
        msg = BASE_DECLINED
        if len(self.note.value) > 0:
            msg += "\n\nThe following feedback has been provided by a developer:\n```"
            msg += self.note.value
            msg += "\n```"
        else:
            msg += "\n\n" + BASE_REASONS
        
        try:
            await user.send(msg)
            await interaction.response.send_message("Feedback submitted.", ephemeral = True)
        except discord.Forbidden:
            await interaction.response.send_message("**ERROR**:warning: Submitter has DMs disabled.", ephemeral = True)

        if len(self.note.value) > 0:
            feedback_log_channel = self.bot.get_channel(config.channels["feedback_log"])
            if feedback_log_channel:
                await feedback_log_channel.send(f"{reviewer.mention}: {self.note.value}")
        
        await interaction.message.delete()

class EditModal(ui.Modal, title="Edit Submission"):
    def __init__(self, bot: commands.Bot, source: str):
        super().__init__()
        self.bot = bot

        top, code = source.split("\n", 1)
        self.top = top
        self.code = code

        self.edit = ui.TextInput(
            label="Module Code",
            required=True,
            style=discord.TextStyle.paragraph,
            default=code
        )

        self.add_item(self.edit)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=f"{self.top}\n{self.edit.value}")

class SubmissionButtons(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        
    def parse_msg(self, content: str):
        try:
            submitter_id = content.split("by: <@")[1].split(">")[0].replace("!", "").replace("&", "")
            submitter_id = int(submitter_id)

            lua_part = content.split("```lua")[1]
            title = lua_part.split('Title = "')[1].split('"')[0]
            artist = lua_part.split('Artist = "')[1].split('"')[0]
            return submitter_id, f'{title} - {artist}'
        except Exception as e:
            return None, None

    @ui.button(label = "Approve", style = discord.ButtonStyle.green, custom_id = "approve_btn")
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        has_role = any(role.id == config.roles["developer"] for role in interaction.user.roles)
        if not has_role:
            return await interaction.response.send_message("**ERROR**:warning: You do not have permission to accept covers.", ephemeral = True)

        submitter_id, title_artist = self.parse_msg(interaction.message.content)

        if not submitter_id:
            return await interaction.response.send_message("**ERROR**:warning: Failed to find submitter id.", ephemeral = True)

        user = await self.bot.fetch_user(submitter_id)
        if not user:
            await interaction.response.send_message("**ERROR**:warning: Failed to find user.", ephemeral = True)

        try:
            await user.send(f"Your cover of **{title_artist}** has been accepted! You can find the song in-game shortly. If this is your first accepted cover, you can find some cover artist rewards in your inventory!")
        except discord.Forbidden:
            await interaction.response.send_message("Submitter has DMs disabled.", ephemeral = True)

        await interaction.message.delete()

    
    @ui.button(label = "Edit", style = discord.ButtonStyle.secondary, custom_id = "edit_btn")
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        has_role = any(role.id == config.roles["developer"] for role in interaction.user.roles)
        if not has_role:
            return await interaction.response.send_message("**ERROR**:warning: You do not have permission to edit covers.", ephemeral = True)

        await interaction.response.send_modal(EditModal(self.bot, interaction.message.content))
        

    @ui.button(label = "Decline", style = discord.ButtonStyle.danger, custom_id = "decline_btn")
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        submitter_id, title_artist = self.parse_msg(interaction.message.content)

        if not submitter_id:
            return await interaction.response.send_message("**ERROR**:warning: Failed to find submitter id.", ephemeral = True)

        await interaction.response.send_modal(FeedbackModal(self.bot, submitter_id, title_artist))

class CoverSubmissionModal(ui.Modal, title = "Cover Submission"):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot
        self.cooldown = 259200 # 259200s=3d

    LYRIC_PLACEHOLDER = '''
    Christmas, Christmas time is near\nTime for toys and time for cheer\n...
    '''
    
    roblox_userid = ui.TextInput(label = "ROBLOX UserId", placeholder = "7949259448")
    title_artist = ui.TextInput(label = "Song Title - Artist", placeholder = "The Chipmunk Song - Alvin & The Chipmunks")
    release_date = ui.TextInput(label = "Release Year", placeholder = "1958")
    lyrics = ui.TextInput(label = "Song Lyrics", style = discord.TextStyle.paragraph, placeholder = LYRIC_PLACEHOLDER)
    audio = ui.Label(text = "Cover Audio File (.mp3/.wav only)", component = ui.FileUpload(min_values = 1, max_values = 1))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True, thinking = True)

        channel = self.bot.get_channel(config.channels["submissions"])

        BASE_STRING = "--!strict\n\nlocal ReplicatedStorage = game:GetService('ReplicatedStorage')\nlocal Types = require(ReplicatedStorage.Types)\n\nreturn {{\n\tTitle = \"{title}\",\n\tArtist = \"{artist}\",\n\tReleaseDate = {date},\n\tDuration = {duration},\n\tCoverBy = {userid},\n\tLyrics = {{\n{lyrics}\t}},\n\tSongId = 0,\n\tVolume = 0.5,\n\tTimePosition = 0\n}} :: Types.Song"

        if channel:
            # one line input
            if self.lyrics.value.count('\n') < 1:
                return await interaction.followup.send("**ERROR**:warning: Submit the lyrics as multiple lines.", ephemeral = True)

            lyrics = ""
            for lyric in self.lyrics.value.split('\n'):
                if lyric.strip():
                    safe_lyric = lyric.replace('"', '\\"')
                    lyrics += f'\t\t{{Text = "{safe_lyric}"}},\n'

            split = self.title_artist.value.split('-')
            title = split[0].strip().replace('"', '\\"')
            artist = split[1].strip().replace('"', '\\"') if len(split) > 1 else "Unknown"
            attachment: discord.Attachment = self.audio.component.values[0]
            
            # non-numeric roblox userid
            if not self.roblox_userid.value.isnumeric():
                return await interaction.followup.send("**ERROR**:warning: Must submit a number for your UserId.", ephemeral = True)

            # non-numeric year input
            if not self.release_date.value.isnumeric():
                return await interaction.followup.send("**ERROR**:warning: Must submit a number for the year.", ephemeral = True)

            # attachment checks
            if not (attachment.filename.lower().endswith(".mp3") or attachment.filename.lower().endswith(".wav")):
                return await interaction.followup.send("**ERROR**:warning: Must submit a `.mp3` or `.wav` file.", ephemeral = True)
            
            # invalid file metadata
            if attachment.content_type not in ["audio/mpeg", "audio/mpeg3", "audio/mp3", "audio/wav", "audio/x-wav"]:
                return await interaction.followup.send("**ERROR**:warning: File metadata does not match `.mp3` or `.wav` format.", ephemeral = True)

            # too large file size (20mb)
            if attachment.size > 20971520:
                return await interaction.followup.send("**ERROR**:warning: Audio file must be 20mb or less.", ephemeral = True)
            
            duration = 0
            file_bytes = await attachment.read()
            try:
                audio = mutagen.File(io.BytesIO(file_bytes))
                if audio is not None and hasattr(audio, 'info'):
                    duration = math.ceil(audio.info.length)
                else:
                    duration = 0
            except Exception as e:
                duration = 0

            if duration == 0:
                return await interaction.followup.send("**ERROR**:warning: Failed to detect file duration", ephemeral = True)

            if duration < 12:
                return await interaction.followup.send("**ERROR**:warning: Please submit a version longer than 12 seconds.", ephemeral = True)

            if duration >= 35:
                return await interaction.followup.send("**ERROR**:warning: Please submit a version shorter than 35 seconds.", ephemeral = True)

            file = await attachment.to_file()
            response = BASE_STRING.format(title = title, artist = artist, date = self.release_date.value, duration = duration, userid = self.roblox_userid.value, lyrics = lyrics)
            
            expiration = time.time() + self.cooldown
            async with aiosqlite.connect(config.database) as database:
                await database.execute(
                    "INSERT OR REPLACE INTO cooldowns (user_id, expiry_time) VALUES (?, ?)",
                    (interaction.user.id, expiration)
                )
                await database.commit()
            
            await channel.send(content = f"Submission by: {interaction.user.mention}\n```lua\n" + response + "```", file = file, view = SubmissionButtons(self.bot))
            await interaction.followup.send(f'Thanks for the submission!', ephemeral = True)
        else:
            await interaction.followup.send(f'**ERROR**:warning: Submission failed. Please try again. If this keeps happening, create a bug report ticket.', ephemeral = True)

class CoverSubmissionButton(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label = "Submit a Cover", style = discord.ButtonStyle.primary, custom_id = "trigger_cover_modal", emoji = "🎤")
    async def trigger(self, interaction: discord.Interaction, button: ui.Button):
        if not not_cover_banned(interaction.user):
            return await interaction.response.send_message(":x: You are blacklisted from submitting covers.", ephemeral = True)
        
        async with aiosqlite.connect(config.database) as database:
            async with database.execute("SELECT expiry_time FROM cooldowns WHERE user_id = ?", (interaction.user.id,)) as cursor:
                row = await cursor.fetchone()
                if row and time.time() < int(row[0]):
                    return await interaction.response.send_message(f":hourglass: You are on cooldown. You can submit again <t:{int(row[0])}:R>", ephemeral = True)

        await interaction.response.send_modal(CoverSubmissionModal(self.bot))

class CoverSubmission(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup.start()

    def cog_unload(self):
        self.cleanup.cancel()
        return super().cog_unload()

    @tasks.loop(hours=24)
    async def cleanup(self):
        async with aiosqlite.connect(config.database) as database:
            await database.execute("DELETE FROM cooldowns WHERE expiry_time < ?", (time.time(),))
            await database.commit()

async def setup(bot: commands.Bot):
    await bot.add_cog(CoverSubmission(bot))
    bot.add_view(SubmissionButtons(bot))
    bot.add_view(CoverSubmissionButton(bot))