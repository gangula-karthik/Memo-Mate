import discord
from discord.ext import commands
from dotenv import load_dotenv
import random
import os
import whisper_backend as wb
from pydub import AudioSegment
import tempfile
import asyncio

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
    files = [discord.File(fp=audio.file, filename=f"{user_id}.{sink.encoding}") for user_id, audio in sink.audio_data.items()]
    print("We have finished recording!")

    transcriptions = []
    loop = asyncio.get_running_loop()  # Get the current event loop
    for user_id, audio in sink.audio_data.items():
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            buffer = audio.file
            buffer.seek(0)
            tmp_file.write(buffer.read())
            tmp_file_name = tmp_file.name

        files.append(discord.File(fp=tmp_file_name, filename=f"{user_id}.{sink.encoding}"))

        transcription = await loop.run_in_executor(None, lambda: wb.transcribe_audio(tmp_file_name))
        transcriptions.append((user_id, transcription))

        os.remove(tmp_file_name)

    print("Finished transcribing audio!")
    transcription_messages = [f"<@{user_id}>: {transcription['outputs']['text']}" for user_id, transcription in transcriptions]
    await channel.send(f"Finished recording audio for: {', '.join(recorded_users)}\n\nTranscriptions:\n" + "\n".join(transcription_messages), files=files)

@bot.command()
async def start(ctx):
    voice = ctx.author.voice

    if not voice:
        await ctx.send_response("You aren't in a voice channel!")

    vc = await voice.channel.connect()
    connections.update({ctx.guild.id: vc}) 

    vc.start_recording(
        discord.sinks.WaveSink(), 
        once_done, 
        ctx.channel
    )
    await ctx.send_response("Started recording!")

@bot.command()
async def stop(ctx):
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        vc.stop_recording() 
        del connections[ctx.guild.id]
        # await ctx.delete()
    else:
        await ctx.send_response("I am currently not recording here.")


if __name__ == "__main__":
    bot.run(TOKEN)
