import os
import shutil
import json
import ffmpeg
import time
import requests

import discord

from exceptions import NoTokenError

with open("token.txt", "r") as file:
    TOKEN = file.read()

if TOKEN == "":
    raise NoTokenError("You must supply a Discord API token in the token.txt file!")

bot = discord.Bot()

def convert_attachment(attachment, target_extension):

    # extract this file's original extension
    original_extension = attachment.split('.')[-1]

    # download the attachment with a unique name
    download_filename = f"{str(time.time())}.{original_extension}"

    # make a download request for the file
    resp = requests.get(attachment, stream=True)

    # write the data we received to a file
    with open(download_filename,"wb") as file:

        resp.raw.decode_content = True

        # copies download data to disk
        shutil.copyfileobj(resp.raw, file)

    # loads file into ffmpeg
    stream = ffmpeg.input(download_filename)

    # Creates output filename
    output_filename = f"{download_filename.split('.')[0]}.{target_extension}"

    # Converts file
    stream = ffmpeg.output(stream,output_filename)

    ffmpeg.run(stream)

    # load the converted file into bytes object
    with open(output_filename, "rb") as file:
        converted_file = file.read()

    # delete the original file
    os.remove(download_filename)
    # delete the converted file
    os.remove(output_filename)

    # return the converted file bytes
    return converted_file

@bot.event
async def on_ready():
    print("Started")

@bot.slash_command(description="Convert referenced video")
async def convert(ctx, target_extension = None):

    # Checks to see if a message to convert was referenced
    if not message.reference:
        await ctx.respond("You did not reference a message to be converted!", empheral=True)
        return

    # Retrieve message to be converted
    referenced_message = await message.channel.fetch_message(message.reference.message_id)

    if not referenced_message.attachments: # Checks if the message has the attribute "attachments"
        await ctx.respond("Message has no attachments!", empheral=True)
        return

    # Loads incompatible file formats
    with open("incompatibles.json","r") as file:
        incompatible_files = json.load(file)

    # we convert every attachment in the message
    for attachment in referenced_message.attachments:

        # make sure the attachment comes from discord's server because i dont trust 3rd parties!
        if not str(attachment).startswith("https://cdn.discordapp.com/attachments"):

            await ctx.respond(
                f"{attachment} could not be converted because it did not come from Discord's servers!"
                empheral=True
            )

            continue
        
        # this file's extension
        extension = str(attachment).split('.')[-1]

        # Checks to see if the file ends with any of the incompatible extensions
        if extension in incompatible_files.keys():
            
            # convert the attachments to target extension
            converted_file = convert_attachment(
                str(attachment),
                target_extension=target_extension
            )

            

        # If we get this point in the code, it means we couldn't find any compatible conversions

        # We will try to extract the file type so we can reply specifying the file type we cant convert.
        # Sometimes this doesnt work because a file wont have an extension we will put it in a try-except block.

        await ctx.respond(f"Unable to convert file type **{failed_extension}**.", empheral=True)

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

        await convert_attachments(reaction.message, requester = user)


    # Delete conversion
    if reaction.emoji == "🗑️":

        print(reaction.message.author.guild_permissions.administrator)

        # Gets the original unconverted message that the conversion is referencing
        reference_message = await reaction.message.channel.fetch_message(reaction.message.reference.message_id)
        # HOLY CRAP THAT IS A MOUTHFUL

        # If the reaction is from who sent the original message (that was converted) or is an admin
        if user.id == reference_message.author.id or reaction.message.author.guild_permissions.administrator:
            await reaction.message.delete()

        # If the user was not the one who sent the original message
        else:
            await reset_reaction("🗑️", reaction.message)

            # Calculates the time elapsed since they last hit the trashcan
            if user.id not in cooldowns:
                cooldowns[user.id] = time.time()

            else:
                elapsed = time.time() - cooldowns[user.id]

                # If it has been less than 10 minutes, we dont send the notification
                if elapsed > 600:
                    return

            await user.send(f"Only the sender of a message can delete its conversion.\n\nLink to original message: {reaction.message.jump_url}")

            cooldowns[user.id] = time.time()

bot.run(TOKEN)
