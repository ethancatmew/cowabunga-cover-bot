import config
import discord
import mutagen
import math
import io
import re
import time
import aiosqlite
from typing import TypedDict, Optional
from discord import ui, app_commands
from discord.ext import commands, tasks

from handlers.cover_submission import on_accept, on_edit, on_reject

class PartialSongSubmissionType(TypedDict):
    title: str
    artist: str
    release_year: int
    genre: list[str]

class SongSubmissionType(PartialSongSubmissionType):
    userid: int
    lyrics: str
    audio: discord.Attachment
    duration: int


class SongInformationModal(ui.Modal, title = "Song Information"):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout = None)
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
                    value = "Pop",
                ),
                discord.CheckboxGroupOption(
                    label = "Classics",
                    value = "Classic",
                    description = "Songs from the 2000s or prior"
                ),
                discord.CheckboxGroupOption(
                    label = "Musicals",
                    value = "Musical"
                ),
                discord.CheckboxGroupOption(
                    label = "Country",
                    value = "Country"
                )
            ]
        )
    )

    async def on_submit(self, interaction: discord.Interaction):
        if not self.release_year.value.isnumeric():
            return await interaction.followup.send("**ERROR**:warning: Must submit a number for your release year.", ephemeral = True)

        song_data = {
            "title": self.song_title.value,
            "artist": self.song_artist.value,
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
        super().__init__(timeout = None)
        self.bot = bot

    @ui.button(label = "Submit Song", style = discord.ButtonStyle.primary, emoji = "🎵", custom_id = "submit_song")
    async def submit_song(self, interaction: discord.Interaction, button: ui.Button):
        is_cover_banned = any(role.id == config.roles["cover_banned"] for role in interaction.user.roles)
        if is_cover_banned:
            return await interaction.response.send_message(":x: You are blacklisted from submitting covers.", ephemeral = True)

        async with aiosqlite.connect(config.database) as database:
            async with database.execute("SELECT expiry_time FROM cooldowns WHERE user_id = ?", (interaction.user.id,)) as cursor:
                row = await cursor.fetchone()
                if row and time.time() < int(row[0]):
                    return await interaction.response.send_message(f":hourglass: You are on cooldown. You can submit again <t:{int(row[0])}:R>", ephemeral = True)

        await interaction.response.send_modal(SongInformationModal(self.bot))

class SubmissionButtons(ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout = None)
        self.bot = bot

    def get_title_artist(self, message: discord.Message):
        content = message.content
        code = re.search(r"```lua\s*(.*?)```", content, re.DOTALL).group(1)
        title = re.search(r'Title\s*=\s*"([^"]*)"', code).group(1)
        artist = re.search(r'Artist\s*=\s*"([^"]*)"', code).group(1)
        return f'{title} - {artist}'

    @ui.button(label = "Approve", style = discord.ButtonStyle.green, custom_id = "approve")
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        return await on_accept.approve(self.bot, interaction, self.get_title_artist(interaction.message))

    @ui.button(label = "Edit", style = discord.ButtonStyle.grey, custom_id = "edit")
    async def edit(self, interaction: discord.Interaction, button: ui.Button):
        return await on_edit.edit(self.bot, interaction)

    @ui.button(label = "Reject", style = discord.ButtonStyle.red, custom_id = "reject")
    async def reject(self, interaction: discord.Interaction, button: ui.Button):
        return await on_reject.reject(self.bot, interaction, self.get_title_artist(interaction.message))


class ContinueView(ui.View):
    def __init__(self, bot: commands.Bot, song_data: PartialSongSubmissionType, interaction: discord.Interaction):
        super().__init__(timeout = 300)
        self.bot = bot
        self.song_data = song_data
        self.original_interaction = interaction

    @ui.button(label = "Next", style = discord.ButtonStyle.primary, emoji = "➡️")
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
            "userid": int(self.roblox_userid.value),
            "lyrics": safe_lyrics,
            "audio": attachment,
            "duration": duration
        }

        genres = ", ".join(f'"{genre}"' for genre in data["genre"])
        lua_str = (
            "```lua\n"
            "return {\n"
            f'\tTitle = "{data["title"]}",\n'
            f'\tArtist = "{data["artist"]}",\n'
            f'\tReleaseDate = {data["release_year"]},\n'
            f'\tGenres = {{{genres}}},\n'
            f'\tDuration = {data["duration"]},\n'
            f'\tCoverBy = {data["userid"]},\n'
            f'\tLyrics = {{\n{data["lyrics"]}\t}},\n'
            f'\tSongId = 0,\n'
            f'\tVolume = 0.5,\n'
            f'\tTimePosition = 0,\n'
            "}\n"
            "```"
        )

        expiration = time.time() + config.cooldown
        async with aiosqlite.connect(config.database) as database:
            await database.execute(
                "INSERT OR REPLACE INTO cooldowns (user_id, expiry_time) VALUES (?, ?)",
                (interaction.user.id, expiration)
            )
            await database.commit()

        file = await attachment.to_file()
        await channel.send(content = f"{interaction.user.id}\n{lua_str}", file = file, view = SubmissionButtons(self.bot))
        await self.continue_view.original_interaction.delete_original_response()
        await interaction.followup.send("Submission received!", ephemeral = True)

class CoverSubmission(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup.start()

    def cog_unload(self):
        self.cleanup.cancel()
        return super().cog_unload()

    @tasks.loop(hours = 24)
    async def cleanup(self):
        async with aiosqlite.connect(config.database) as database:
            await database.execute("DELETE FROM cooldowns WHERE expiry_time < ?", (time.time(),))
            await database.commit()

    @app_commands.command(name = "setup_submission", description = "Create the song submission button")
    async def setup_submission(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            config.cover_rules,
            view = StartSubmissionView(self.bot)
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(CoverSubmission(bot))
    bot.add_view(StartSubmissionView(bot))
    bot.add_view(SubmissionButtons(bot))