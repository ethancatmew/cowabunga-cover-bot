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
        cover_banned_role = 1472156962081996892
        return not any(role.id == cover_banned_role for role in user.roles)

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
            feedback_log_channel = self.bot.get_channel(1357438360167252008)
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
        has_role = any(role.id == 1353545674335191122 for role in interaction.user.roles)
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


        try:
            # attempt to upload the audio

            

            await interaction.message.delete()
        except:
            # audio failed to upload, for whatever reason. don't delete
            await interaction.response.send_message("Audio failed to upload to ROBLOX", ephemeral = True)

    
    @ui.button(label = "Edit", style = discord.ButtonStyle.secondary, custom_id = "edit_btn")
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        has_role = any(role.id == 1353545674335191122 for role in interaction.user.roles)
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
        self.submission_channel = 1470601268731969832
        self.cooldown = 259200 # 259200

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

        channel = self.bot.get_channel(self.submission_channel)

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
            async with aiosqlite.connect("database.db") as database:
                await database.execute(
                    "INSERT OR REPLACE INTO cooldowns (user_id, expiry_time) VALUES (?, ?)",
                    (interaction.user.id, expiration)
                )
                await database.commit()
            
            await channel.send(content = f"Submission by: {interaction.user.mention}\n```lua\n" + response + "```", file = file, view = SubmissionButtons(self.bot))
            await interaction.followup.send(f'Thanks for the submission!', ephemeral = True)
        else:
            await interaction.followup.send(f'**ERROR**:warning: Submission failed. Please try again. If this keeps happening, create a bug report ticket.', ephemeral = True)

class CoverSubmissionTrigger(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.database = "database.db"

    @ui.button(label = "Submit a Cover", style = discord.ButtonStyle.primary, custom_id = "trigger_cover_modal", emoji = "🎤")
    async def trigger(self, interaction: discord.Interaction, button: ui.Button):
        if not not_cover_banned(interaction.user):
            return await interaction.response.send_message(":x: You are blacklisted from submitting covers.", ephemeral = True)
        
        async with aiosqlite.connect(self.database) as database:
            async with database.execute("SELECT expiry_time FROM cooldowns WHERE user_id = ?", (interaction.user.id,)) as cursor:
                row = await cursor.fetchone()
                if row and time.time() < int(row[0]):
                    return await interaction.response.send_message(f":hourglass: You are on cooldown. You can submit again <t:{int(row[0])}:R>", ephemeral = True)

        await interaction.response.send_modal(CoverSubmissionModal(self.bot))

class CoverSubmission(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.database = "database.db"
        self.cleanup.start()

    def cog_unload(self):
        self.cleanup.cancel()
        return super().cog_unload()

    @tasks.loop(hours=24)
    async def cleanup(self):
        async with aiosqlite.connect(self.database) as database:
            await database.execute("DELETE FROM cooldowns WHERE expiry_time < ?", (time.time(),))
            await database.commit()

    @app_commands.command(name = "post_cover_button")
    @app_commands.checks.has_any_role(1353545674335191122, 1471636534225801278)
    async def post_button(self, interaction: discord.Interaction):
        rules = ("""# Cover Submissions
By submitting a cover, you allow the developers to use your submitted audio in any of their games. You may request to have your audio removed.
If accepted, you will receive: a chat tag, a door, and a door effect as compensation. 

## Tips
1. Record your cover in a quiet space. We will not accept covers that have lots of feedback / background noise.
2. Listen to the original song you are trying to cover before recording your own version. This will help you stay in pitch and on time.
3. Keep your recordings between 12 and 35 seconds. Anything shorter or longer will fail to submit.
4. Submit your raw vocals. We will not accept any cover with extra effects.
5. Keep covers to English only. There will be very few exceptions for songs in other languages.
6. Sing the chorus or the most popular part of the song. Start at the beginning of a verse.

## FAQ
- How long does it take for my cover to be reviewed?
  - There is no exact time frame, it depends on how busy the developers are with other projects or personal life. We do have some volunteers who can decline covers more frequently but being accepted may take multiple weeks or longer.
- What songs are currently in the game?
  - [Click Here](<https://pastebin.com/rpYgpesT>)
- Can we submit any songs?
  - You are allowed to submit any song, however it may be declined if it is not popular enough, sung in any language other than English, or contains language against ROBLOX rules.

## How will I know if I get accepted?
To receive your result you must have your direct messages enabled for the server. You will receive a DM from the bot telling you whether or not your cover has been added to the game.
If your cover is added, you should see the rewards in your inventory the next time you log in! If you do not see them, please go to <#1357424462093353060> with your UserId and song.

:warning: Asking for your cover to be checked or complaining about response time will result in your cover being declined.""")
        await interaction.channel.send(content=rules, view = CoverSubmissionTrigger(self.bot))
        await interaction.response.send_message("Posted cover button!", ephemeral = True)

    @post_button.error
    async def post_button_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(":no_entry_sign: You must be a part of the Cowabunga Team to use this command.", ephemeral = True)

    @app_commands.command(name = "clear_cooldown", description = "Clear cover submission cooldown for a specific user.")
    @app_commands.checks.has_any_role(1353545674335191122, 1471636534225801278)
    async def clear_cooldown(self, interaction: discord.Interaction, member: discord.Member):
        async with aiosqlite.connect(self.database) as database:
            await database.execute("DELETE FROM cooldowns WHERE user_id = ?", (member.id,))
            await database.commit()
        await interaction.response.send_message(f"Cleared cover submission cooldown for {member.mention}.", ephemeral = True)
    
    @clear_cooldown.error
    async def clear_cooldown_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(":no_entry_sign: You must be a part of the Cowabunga Team to use this command.", ephemeral = True)

    @app_commands.command(name = "post_covers_disabled")
    @app_commands.checks.has_any_role(1353545674335191122, 1471636534225801278)
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


async def setup(bot: commands.Bot):
    await bot.add_cog(CoverSubmission(bot))
    bot.add_view(SubmissionButtons(bot))
    bot.add_view(CoverSubmissionTrigger(bot))