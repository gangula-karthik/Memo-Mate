import discord
from discord.ext import commands
from dotenv import load_dotenv
import random
import os
import whisper_backend as wb

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()
intents.messages = True
connections = {}

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name}')

async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    recorded_users = [
        f"<@{user_id}>"
        for user_id, audio in sink.audio_data.items()
    ]
    await sink.vc.disconnect()
    files = [discord.File(audio.file, f"{user_id}.{sink.encoding}") for user_id, audio in sink.audio_data.items()]
    print("We have finished recording!")
    print("Started transcribing audio...")
    res = wb.transcribe_audio(sink.audio_data)
    print(res)
    await channel.send(f"finished recording audio for: {', '.join(recorded_users)}", files=files)

@bot.command()
async def start(ctx):
    voice = ctx.author.voice

    if not voice:
        await ctx.respond("You aren't in a voice channel!")

    vc = await voice.channel.connect()
    connections.update({ctx.guild.id: vc}) 

    vc.start_recording(
        discord.sinks.MP4Sink(), 
        once_done, 
        ctx.channel
    )
    await ctx.respond("Started recording!")

@bot.command()
async def stop(ctx):
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        vc.stop_recording() 
        del connections[ctx.guild.id]
        await ctx.delete()
    else:
        await ctx.respond("I am currently not recording here.")


if __name__ == "__main__":
    bot.run(TOKEN)
