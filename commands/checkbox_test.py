import config
import discord
import mutagen
import math
import io
from typing import TypedDict, Optional
from discord import ui, app_commands
from discord.ext import commands

from handlers.cover_submission import on_accept

class PartialSongSubmissionType(TypedDict):
    song_title: str
    song_artist: str
    release_year: int
    genre: list[str]

class SongSubmissionType(PartialSongSubmissionType):
    roblox_userid: int
    lyrics: str
    audio: discord.Attachment
    duration: int


class SongInformationModal(ui.Modal, title = "Song Information"):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    song_title = ui.TextInput(
        label = "Song Title",
        required = True,
        style = discord.TextStyle.short
    )

    song_artist = ui.TextInput(
        label = "Song Artist",
        required = True,
        style = discord.TextStyle.short
    )

    release_year = ui.TextInput(
        label = "Release Year",
        required = True,
        style = discord.TextStyle.short
    )

    genre = ui.Label(
        text = "Genre",
        component = ui.CheckboxGroup(
            custom_id = "genre",
            required = True,
            min_values = 1,
            max_values = 3,
            options = [
                discord.CheckboxGroupOption(
                    label = "Pop",
                    value = "pop",
                ),
                discord.CheckboxGroupOption(
                    label = "Classic",
                    value = "classic",
                    description = "Songs from the 2000s or prior"
                ),
                discord.CheckboxGroupOption(
                    label = "Rock",
                    value = "rock"
                ),
                discord.CheckboxGroupOption(
                    label = "Country",
                    value = "country"
                )
            ]
        )
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not self.release_year.value.isnumeric():
            return await interaction.followup.send("**ERROR**:warning: Must submit a number for your release year.", ephemeral = True)

        song_data = {
            "song_title": self.song_title.value,
            "song_artist": self.song_artist.value,
            "release_year": int(self.release_year.value),
            "genre": self.genre.component.values
        }

        await interaction.response.send_message(
            "Click **Next** to submit the audio information.",
            ephemeral = True,
            view = ContinueView(self.bot, song_data, interaction)
        )

class StartSubmissionView(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label = "Submit Song", style = discord.ButtonStyle.primary, emoji = "🎵", custom_id = "submit_song")
    async def submit_song(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SongInformationModal(self.bot))

class SubmissionButtons(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label = "Approve", style = discord.ButtonStyle.green, custom_id = "approve")
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        return await on_accept(self.bot, interaction, "test")


class ContinueView(ui.View):
    def __init__(self, bot: commands.Bot, song_data: PartialSongSubmissionType, interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.bot = bot
        self.song_data = song_data
        self.original_interaction = interaction

    @ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AudioSubmissionModal(self.bot, self))

class AudioSubmissionModal(ui.Modal, title = "Audio Submission"):
    def __init__(self, bot: commands.Bot, continue_view: ContinueView):
        super().__init__()
        self.bot = bot
        self.continue_view = continue_view

    roblox_userid = ui.TextInput(
        label = "Roblox UserId",
        required = True,
        style = discord.TextStyle.short
    )

    lyrics = ui.TextInput(
        label = "Song Lyrics",
        required = True,
        style = discord.TextStyle.paragraph
    )

    audio = ui.Label(
        text = "Cover Audio",
        component = ui.FileUpload(
            min_values = 1,
            max_values = 1
        )
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral = True)

        channel = self.bot.get_channel(config.channels["submissions"])
        if not channel:
            await interaction.followup.send(f'**ERROR**:warning: Submission failed. Please try again. If this keeps happening, create a bug report ticket.', ephemeral = True)

        attachment: discord.Attachment = self.audio.component.values[0]

        if not self.roblox_userid.value.isnumeric():
            return await interaction.followup.send("**ERROR**:warning: Must submit a number for your UserId.", ephemeral = True)

        if self.lyrics.value.count('\n') < 1:
            return await interaction.followup.send("**ERROR**:warning: Submit the lyrics as multiple lines.", ephemeral = True)

        safe_lyrics = ""
        for lyric in self.lyrics.value.split('\n'):
            if lyric.strip():
                safe_lyric = lyric.replace('"', '\\"')
                safe_lyrics += f'\t\t{{Text = "{safe_lyric}"}},\n'

        if not (attachment.filename.lower().endswith(".mp3") or attachment.filename.lower().endswith(".wav")):
            return await interaction.followup.send("**ERROR**:warning: Must submit a `.mp3` or `.wav` file.", ephemeral = True)

        if attachment.content_type not in ["audio/mpeg", "audio/mpeg3", "audio/mp3", "audio/wav", "audio/x-wav"]:
            return await interaction.followup.send("**ERROR**:warning: File metadata does not match `.mp3` or `.wav` format. Try using a different online converter?", ephemeral = True)

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

        data: SongSubmissionType = {
            **self.continue_view.song_data,
            "roblox_userid": int(self.roblox_userid.value),
            "lyrics": safe_lyrics,
            "audio": attachment,
            "duration": duration
        }

        await channel.send(content = interaction.user.id)

        await self.continue_view.original_interaction.delete_original_response()
        await interaction.followup.send("Submission received!", ephemeral = True)

class CheckboxTest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name = "setup_submission", description = "Create the song submission button")
    async def setup_submission(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            config.cover_rules,
            view = StartSubmissionView(self.bot)
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(CheckboxTest(bot))