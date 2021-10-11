from __future__ import unicode_literals
import os
import shutil
import json
import ffmpeg
import time
import requests
import youtube_dl
import discord
from discord.ext import commands

ytdl = youtube_dl.YoutubeDL()

bot = commands.Bot(command_prefix = "!")

@bot.event
async def on_ready():
    print("Started")

@bot.event
async def on_message(message):
    try:
        # For every attachment in the message
        for attachment in message.attachments:
            # If the attachment comes from discord's servers
            if str(attachment).startswith("https://cdn.discordapp.com/attachments"):

                # Loads incompatible file formats
                file = open("incompatibles.json","r")
                incompatible_files = json.load(file)
                file.close()

                # Checks to see if the file ends with any of the incompatible extensions
                for extension in incompatible_files.keys():
                    if str(attachment).endswith(extension):

                        # Gets the target extension from the incompatible files dictionary
                        target_extension = incompatible_files[extension]

                        # Notifies user that we are converting their file
                        await message.channel.send(f"Converting **{extension}** to **{target_extension}**")

                        # Create unique filename
                        download_filename = f"{int(time.time())}.{extension}"

                        # Makes request
                        r = requests.get(str(attachment), stream=True)

                        # Opens downloaded file
                        file = open(download_filename,"wb")
                        r.raw.decode_content = True

                        # Copies request data to file
                        shutil.copyfileobj(r.raw, file)

                        # Closes downloaded file
                        file.close()

                        # Loads file into ffmpeg
                        stream = ffmpeg.input(download_filename)

                        # Creates output filename
                        output_file_name = f"{download_filename.split('.')[0]}.{target_extension}"

                        # Converts file
                        stream = ffmpeg.output(stream,output_file_name)

                        ffmpeg.run(stream)

                        # Sends converted file
                        await message.channel.send(file = discord.File(output_file_name))

                        os.remove(download_filename)
                        os.remove(output_file_name)
    except:
        await ctx.send("Something went wrong during conversion.")


bot.run("I never push tokens to GitHub ever")
