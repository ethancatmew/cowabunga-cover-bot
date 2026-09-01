import config
import discord
from discord import ui, app_commands
from discord.ext import commands

class SongInformationModal(ui.Modal, title="Song Information"):
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
        song_data = {
            "song_title": self.song_title.value,
            "song_artist": self.song_artist.value,
            "release_year": self.release_year.value,
            "genre": self.genre.component.values
        }

        await interaction.response.send_message(
            "Click **Next** to submit the audio information.",
            ephemeral = True,
            view = ContinueView(song_data)
        )

class StartSubmissionView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label = "Submit Song", style = discord.ButtonStyle.primary, emoji = "🎵", custom_id = "submit_song")
    async def submit_song(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(SongInformationModal())

class ContinueView(ui.View):
    def __init__(self, song_data: dict):
        super().__init__(timeout=300)
        self.song_data = song_data

    @ui.button(label="Next", style=discord.ButtonStyle.primary, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AudioSubmissionModal(self.song_data))

class AudioSubmissionModal(ui.Modal, title="Audio Submission"):
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

    def __init__(self, song_data: dict):
        super().__init__()
        self.song_data = song_data

    async def on_submit(self, interaction: discord.Interaction):
        attachment: discord.Attachment = self.audio.component.values[0]

        data = {
            **self.song_data,
            "roblox_userid": self.roblox_userid.value,
            "lyrics": self.lyrics.value,
            "audio": attachment
        }

        await interaction.response.send_message(
            "Submission received!\n\n"
            f"**Song:** {data['song_title']}\n"
            f"**Artist:** {data['song_artist']}\n"
            f"**Release Year:** {data['release_year']}\n"
            f"**Genre:** {', '.join(data['genre'])}\n"
            f"**Roblox UserId:** {data['roblox_userid']}\n"
            f"**Audio:** {data['audio'].filename}",
            ephemeral=True
        )

class CheckboxTest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name = "setup_submission", description = "Create the song submission button")
    async def setup_submission(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            config.cover_rules,
            view=StartSubmissionView()
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(CheckboxTest(bot))