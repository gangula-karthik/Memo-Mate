import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import whisper_backend as wb
import tempfile
import asyncio
import requests
import gc

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
HF_TOKEN = os.getenv('HF_TOKEN')

intents = discord.Intents.all()
intents.messages = True
connections = {}

bot = commands.Bot(intents=intents)
recordings = bot.create_group("recording", "You can start/stop the recording")
tasks = bot.create_group("tasks", "You can ask the bot questions based on your audio recordings")

transcription = "Empty transcription"


@bot.event
async def on_ready():
    # bot.change_presence(status=discord.Status.Online, activity=discord.game('a video game'))
    print(f'We have logged in as {bot.user.name}')

async def disconnect_vc(sink):
    await sink.vc.disconnect()
    print("Disconnected from voice channel.")

async def create_temp_files(sink):
    temp_files = []
    for user_id, audio in sink.audio_data.items():
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            buffer = audio.file
            buffer.seek(0)
            tmp_file.write(buffer.read())
            temp_files.append((user_id, tmp_file.name))
    return temp_files

async def transcribe_audio_file(user_id, file_path, loop):
    transcription = await loop.run_in_executor(None, lambda: wb.transcribe_audio(file_path))
    return user_id, transcription

async def cleanup_files(files):
    for _, file_path in files:
        os.remove(file_path)
    gc.collect()

async def send_transcription_messages(channel, recorded_users, transcriptions, files):
    global transcription
    transcription_messages = [f"<@{user_id}>: {transcription['outputs']['text']}" for user_id, transcription in transcriptions]
    transcription = "\n".join(transcription_messages)
    await channel.send(f"Finished recording audio for: {', '.join(recorded_users)}\n\nTranscriptions:\n" + "\n".join(transcription_messages), files=files)

async def once_done(sink: discord.sinks, channel: discord.TextChannel, *args):
    recorded_users = [f"<@{user_id}>" for user_id, _ in sink.audio_data.items()]
    await disconnect_vc(sink)

    temp_files = await create_temp_files(sink)
    files = [discord.File(fp=file_path, filename=f"{user_id}.{sink.encoding}") for user_id, file_path in temp_files]

    loop = asyncio.get_running_loop()
    transcription_tasks = [transcribe_audio_file(user_id, file_path, loop) for user_id, file_path in temp_files]
    transcriptions = await asyncio.gather(*transcription_tasks)

    await cleanup_files(temp_files)
    await send_transcription_messages(channel, recorded_users, transcriptions, files)

@recordings.command(description="Start recording audio in the voice channel you are in.")
async def start(ctx):
    voice = ctx.author.voice

    if not voice:
        await ctx.send_response("You aren't in a voice channel!")

    try:
        vc = await voice.channel.connect()
    except AttributeError:
        await ctx.send_response("I am already recording in this voice channel.")
        return
    
    connections.update({ctx.guild.id: vc}) 

    vc.start_recording(
        discord.sinks.WaveSink(), 
        once_done, 
        ctx.channel
    )
    await ctx.send_response("🎙️ Started recording!")

@recordings.command(description="Stop recording audio in the voice channel you are in.")
async def stop(ctx):
    if ctx.guild.id in connections:
        vc = connections[ctx.guild.id]
        vc.stop_recording() 
        del connections[ctx.guild.id]
    else:
        await ctx.send_response("I am currently not recording here.")

@tasks.command(description="Get the bot to give you a summary of the audio recording.")
async def summary(ctx):
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    payload = {
        "inputs": f"Please summarize the key points and decisions made in the audio recording: {transcription}."
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload, headers={"Authorization": f"Bearer {HF_TOKEN}"}) as response:
            if response.status == 200:
                output = await response.json()
                summary = output[0].get('generated_text', 'Summary not available.')
                await ctx.send(summary)
            else:
                await ctx.send("Failed to generate summary, please try again later.")


if __name__ == "__main__":
    bot.run(TOKEN)
