import config
import discord
import os
import re
from discord.ext import commands
from . import opencloud

async def approve(bot: commands.Bot, interaction: discord.Interaction, title_artist: str):
    has_role = any(role.id in {config.roles["developer"], config.roles["dev_test"]} for role in interaction.user.roles)
    if not has_role:
        return await interaction.response.send_message("**ERROR**:warning: You do not have permission to accept covers.", ephemeral = True)

    content = interaction.message.content

    submitter_id = int(content.splitlines()[0])
    user = await bot.fetch_user(submitter_id)
    if not user:
        await interaction.response.send_message("**ERROR**:warning: Failed to find user.", ephemeral = True)
        return

    await interaction.response.defer(ephemeral = True)

    try:
        source = re.search(r"```lua\s*(.*?)```", content, re.DOTALL | re.IGNORECASE).group(1).strip()
        song_name = re.search(r'Title\s*=\s*"([^"]*)"', source).group(1)

        attachment = interaction.message.attachments[0]
        extension = os.path.splitext(attachment.filename)[1].lower()

        if extension not in {".wav", ".mp3"}:
            return await interaction.followup.send("Only `.mp3` or `.wav` file extension is allowed", ephemeral = True)

        os.makedirs("./audio_queue", exist_ok = True)
        file_path = os.path.join("./audio_queue", f"{song_name}{extension}")

        await attachment.save(file_path, seek_begin=True)
        audio_result = await opencloud.upload_file(file_path, "audio")

        source = source.replace("SongId = 0", f"SongId = {audio_result.get('asset_id')}")
        luau = f"""local ReplicatedStorage = game:GetService("ReplicatedStorage")
local AssetService = game:GetService("AssetService")

local songs = ReplicatedStorage:FindFirstChild("Songs")

if not songs then
    error("ReplicatedStorage.Songs does not exist")
end

local module = Instance.new("ModuleScript")
module.Name = {song_name!r}
module.Source = [[{source}]]
module.Parent = songs

print("Created module:", module:GetFullName())

local success, err = pcall(function()
    AssetService:SavePlaceAsync({{
        SaveWithoutPublish = true
    }})
end)

return {{
    success = true,
    name = module.Name,
    path = module:GetFullName(),
    saved = true
}}"""

        result = await opencloud.run_luau(luau)
        print(result)
        if result.get("error"):
            return await interaction.followup.send(f"Failed to create module: `{result['error']}`", ephemeral = True)

        await user.send(f"Your cover of **{title_artist}** has been accepted! You can find the song in-game shortly. If this is your first accepted cover, you can find some cover artist rewards in your inventory!")
    except discord.Forbidden:
        return await interaction.followup.send("Submitter has DMs disabled.", ephemeral = True)

    await interaction.message.delete()