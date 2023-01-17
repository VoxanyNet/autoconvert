import os
import shutil
import json
import time
import logging

import ffmpeg
import requests
import discord
import tomlkit as toml

from exceptions import NoTokenError

with open("/etc/autoconvert.conf", "r") as file:
    config = toml.parse(file.read())

# parse config file
TOKEN = config["bot_token"]
INCOMPATIBLE_FILES = config["incompatibles"]

if TOKEN == "":
    raise NoTokenError("You must supply a Discord API token in the token.txt file!")

# Stores trashcan notification cooldowns
cooldowns = {}

# stores the original messages that resulted in a conversion
# if one of these messges are deleted then we delete the conversion as well
# original_message_id : conversion_message_id
converted_messages_map = {}

intents = discord.Intents.all()
bot = discord.Bot(intents=intents)

async def reset_reaction(emoji_to_remove, message):

    users_to_remove = []

    # This credasiu;dhjashiuosadpjo0iasd0ijhasojistjoidsgiohjfdsahipuofdshijopdsfjiopdfsfjdiosfsdjiopfxdiojdsjifdsfsdfates a list of the users who reacted that doesn't include the bot
    for _reaction in message.reactions:
        if _reaction.emoji == emoji_to_remove:
            async for user in _reaction.users():
                # We only want to remove reactions from other users
                if user.id != message.author.id:
                    users_to_remove.append(user)

    for user_id in users_to_remove:
        await message.remove_reaction(emoji_to_remove,user)

async def convert_attachments(message, requester = None):

    # If we are given the user who requested the conversion, we will mention them when its complete
    if requester:
        requester_mention = f"<@{requester.id}>\n"
    else:
        requester_mention = ""

    for attachment in message.attachments:
        # If the attachment comes from discord's servers
        if str(attachment).startswith("https://cdn.discordapp.com/attachments"):

            # Checks to see if the file ends with any of the incompatible extensions
            for extension in INCOMPATIBLE_FILES.keys():
                if str(attachment).endswith(extension):
                    # Gets the target extension from the incompatible files dictionary
                    target_extension = INCOMPATIBLE_FILES[extension]

                    # Notifies user that we are converting their file
                    notify_message = await message.channel.send(f"🔄 Converting **{extension}** to **{target_extension}**")

                    async with message.channel.typing(): # Use typing as an indicator
                    # Typing indicator goes away once a message is sent

                        # Create unique filename
                        download_filename = f"/tmp/{str(time.time())}.{extension}"

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
                        output_file_name = f"/tmp/{download_filename.split('.')[0]}.{target_extension}"

                        # Converts file
                        stream = ffmpeg.output(stream,output_file_name)

                        ffmpeg.run(stream)

                        # Sends converted file
                        try:
                            conversion_message = await message.reply(f"{requester_mention}✅ Converted **{extension}** to **{target_extension}**", file = discord.File(output_file_name), mention_author=False)
                        except:
                            conversion_message = await message.reply(f"{requester_mention}**Something went wrong with uploading the conversion.**\n\nThis probably means the conversion result was too large to be sent.",mention_author=False)

                    await notify_message.delete()

                    await conversion_message.add_reaction("🗑️")
                    
                    converted_messages_map[message.id] = conversion_message.id

                    os.remove(download_filename)
                    os.remove(output_file_name)

                    break

@bot.event
async def on_ready():
    print("Started")

@bot.event
async def on_message_delete(message):

    print(message.id)

    print(converted_messages_map)

    # if we find that a message we converted has been deleted, we delete our conversion
    if message.id in converted_messages_map.keys():
        # fetch our conversion message
        conversion_message_id = converted_messages_map[message.id]
        conversion_message = await message.channel.fetch_message(conversion_message_id)

        # actually delete our conversion message
        await conversion_message.delete()

@bot.event
async def on_message(message):

    # we dont check for messages that we sent ourself
    if message.author == bot.user:
        return

    # Checks if the bot was manually mentioned
    if bot.user in message.mentions:
        # Checks to see if a message to convert was referenced
        if not message.reference:
            await message.reply("You did not reference a message to be converted!")
            return

        # Retrieve message to be converted
        referenced_message = await message.channel.fetch_message(message.reference.message_id)

        if not referenced_message.attachments: # Checks if the message has the attribute "attachment"
            await message.reply("Message has no attachments!")
            return
            
        for attachment in referenced_message.attachments:

            # If the attachment comes from discord's servers
            if not str(attachment).startswith("https://cdn.discordapp.com/attachments"):
                await message.reply(f"{attachment} could not be converted because it did not come from Discord's servers!")
                continue

            # Checks to see if the file ends with any of the incompatible extensions
            for extension in INCOMPATIBLE_FILES.keys():
                if str(attachment).endswith(extension):

                    # Adds confirmation button
                    await convert_attachments(referenced_message, message.author)

                    # If we find at least one attachment that
                    # could be converted we dont need to check
                    # for any others, thus the return
                    return

            # If we get this point in the code, it means we couldn't find any compatible conversions

            # We will try to extract the file type so we can reply specifying the file type we cant convert.
            # Sometimes this doesnt work because a file wont have an extension we will put it in a try-except block.
            try:
                failed_extension = f" **{str(attachment).split('.')[-1]}**"
            except:
                failed_extension = ""

                raise

            await message.reply(f"Unable to convert file type{failed_extension}.")

    # Automatically places a convert button on message detected to be convertible
    for attachment in message.attachments:
        # If the attachment comes from discord's servers
        if attachment.url.startswith("https://cdn.discordapp.com/attachments"):

            # Checks to see if the file ends with any of the incompatible extensions
            for extension in INCOMPATIBLE_FILES.keys():
                if attachment.url.endswith(extension):

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

        await convert_attachments(reaction.message, requester = user)


    # Delete conversion
    if reaction.emoji == "🗑️":

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

