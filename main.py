import os
import shutil
import json
import ffmpeg
import time
import requests
import discord
from discord.ext import commands
import discord.utils
import youtube_dl

# Make the bot delete messages if the OP deletes their message
# Maybe add a little trashcan emote to message and it just listens for that event
bot = commands.Bot(command_prefix = "!")

bot.ytdl = youtube_dl.YoutubeDL({"outtmpl": "downloads/%(id)s.%(ext)s"})

async def reset_reaction(emoji_to_remove, message):

    users_to_remove = []

    # This creates a list of the users who reacted that doesn't include the bot
    for _reaction in message.reactions:
        if _reaction.emoji == emoji_to_remove:
            async for user in _reaction.users():
                # We only want to remove reactions from other users
                if user.id != message.author.id:
                    users_to_remove.append(user)

    for user_id in users_to_remove:
        await message.remove_reaction(emoji_to_remove,user)

async def convert_attachments(message):
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
                    async with message.channel.typing():
                        # Gets the target extension from the incompatible files dictionary
                        target_extension = incompatible_files[extension]

                        # Notifies user that we are converting their file
                        notify_message = await message.channel.send(f"🔄 Converting **{extension}** to **{target_extension}**")

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
                        conversion_message = await message.reply(f"✅ Converted **{extension}** to **{target_extension}**", file = discord.File(output_file_name))

                        await notify_message.delete()
                        
                        await conversion_message.add_reaction("🗑️")

                        os.remove(download_filename)
                        os.remove(output_file_name)

                    break

@bot.event
async def on_ready():
    print("Started")

@bot.event
async def on_message(message):

    # Checks to see if the message has any attachments that can be converted
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

                    # Adds confirmation button
                    await message.add_reaction("🔄")

                    # If we find at least one attachment that
                    # could be converted we dont need to check
                    # for any others, thus the return
                    return

@bot.event
async def on_reaction_add(reaction, user):

    # We only care about reactions if the bot was the first one to react
    if bot.user not in await reaction.users().flatten():
        return

    # We also dont care about reactions sent from the bot
    if bot.user.id == user.id:
        return

    # Confirmed conversion
    if reaction.emoji == "🔄":

        await reset_reaction("🔄", reaction.message)

        await convert_attachments(reaction.message)


    # Delete conversion
    if reaction.emoji == "🗑️":

        # Gets the original unconverted message that the conversion is referencing
        reference_message = await reaction.message.channel.fetch_message(reaction.message.reference.message_id)
        # HOLY CRAP THAT IS A MOUTHFUL

        # If the reaction is from who sent the original message (that was converted)
        if user.id == reference_message.author.id:
            await reaction.message.delete()

        # If the user was not the one who sent the original message
        else:
            await reset_reaction("🗑️", reaction.message)


bot.run("ODkzNjE1NDQ2NTMwNjAwOTYx.YVeCPQ.3XZ111ChZJY03JreMNOwOiBl-Gk")
