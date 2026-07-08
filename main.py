from dotenv import load_dotenv
import os
import discord
import aiosqlite
from discord.ext import commands

bot = commands.Bot(command_prefix = '$', intents = discord.Intents.all())

load_dotenv()

async def load_cogs():
    for filename in os.listdir('./commands'):
        if filename.endswith('.py'):
            await bot.load_extension(f'commands.{filename[:-3]}')
    print('Cogs loaded')

async def load_database():
    async with aiosqlite.connect("database.db") as database:
        await database.execute("""
            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id INTEGER PRIMARY KEY,
                expiry_time REAL
            )                    
        """)
        await database.commit()
        print('Database loaded')

@bot.event
async def on_ready():
    await load_database()
    await load_cogs()
    synced = await bot.tree.sync()
    await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Join our group!"))
    print(f'{bot.user} is now online, synced {len(synced)} commands.')

@bot.event
async def on_app_command_error(interaction, error):
    print(repr(error))

##==- Load Bot -==##
bot.run(os.getenv("DISCORD_BOT"))