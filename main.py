import os
import shutil
import json
import time
from io import BytesIO

import ffmpeg
import requests

import discord

from exceptions import NoTokenError

with open("token.txt", "r") as file:
    TOKEN = file.read()

if TOKEN == "":
    raise NoTokenError("You must supply a Discord API token in the token.txt file.")

# create bot object
intents = discord.Intents.default()
bot = discord.Bot(intents=intents)


def convert_attachment(attachment: str, target_extension: str) -> BytesIO:

    # extract this file's original extension
    original_extension = attachment.split('.')[-1]

    # download the attachment with a unique name
    download_filename = f"{str(time.time())}.{original_extension}"

    # make a download request for the file
    resp = requests.get(attachment, stream=True)

    # write the data we received to a file
    with open(download_filename, "wb") as file:

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
        converted_file = BytesIO(
            file.read()
        )

    # delete the original file
    os.remove(download_filename)
    # delete the converted file
    os.remove(output_filename)

    # return the converted file bytes
    return converted_file

@bot.slash_command(description="Convert the attachment of a message")
async def convert(ctx, message_url, target_extension=None):

    # the message ID is the last part of the URL
    referenced_message_id = message_url.split("/")[-1]

    # we will only convert messages that are in the same guild
    referenced_message = await ctx.channel.fetch_message(referenced_message_id)

    if not referenced_message.attachments:  # Checks if the message has the attribute "attachments"
        await ctx.respond("Message has no attachments!", ephemeral=True)
        return

    # we only convert the first attachment
    if len(referenced_message.attachments) > 1:
        await ctx.respond("Message has more than one attachment, only converting the first one.", ephemeral=True)

    attachment = referenced_message.attachments[0]

    # make sure the attachment comes from discord's server because i dont trust 3rd parties!
    if not attachment.url.startswith("https://cdn.discordapp.com/attachments"):

        await ctx.respond(
            f"{attachment.filename} could not be converted because it did not come from Discord's servers!",
            ephemeral=True
        )

        return

    # this file's extension
    extension = attachment.url.split('.')[-1].lower()

    # if the user did not supply a target extension, we look up a suitable one
    if target_extension is None:

        # loads suitable format map
        with open("incompatibles.json", "r") as file:
            incompatible_files = json.load(file)

        # lookup suitable format
        try:
            target_extension = incompatible_files[extension]

        # if we cannot find a suitable file format, then we notify them
        except KeyError:
            await ctx.respond(f"Unable to convert file type **{extension}**.", ephemeral=True)

            return

    # convert the attachments to target extension
    converted_file = convert_attachment(
        attachment.url,
        target_extension=target_extension
    )

    # put converted file into Discord file object
    converted_attachment = discord.File(
        fp=converted_file,
        filename=f"{attachment.filename}.{target_extension}",
        spoiler=attachment.is_spoiler(),
        description=attachment.description
    )

    # send all the converted attachments
    await ctx.respond(
        file=converted_attachment
    )

bot.run(TOKEN)
