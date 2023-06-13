import discord
import os
from dotenv import load_dotenv

load_dotenv()
key = os.environ["TOKEN"]

CHANNEL_ID_GENERAL = 970095404031033374
CHANNEL_ID_UNSIGN = 1118182973037092884

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("$hello"):
        await message.channel.send("Hello!")


@client.event
async def on_raw_reaction_remove(data):
    guild = client.get_guild(data.guild_id)
    ctxChannel = guild.get_channel(data.channel_id)
    tarChannel = discord.utils.get(guild.channels, id=CHANNEL_ID_UNSIGN)

    print("Someone just removed reaction")

    raid = "SADPEPE"
    message = await ctxChannel.fetch_message(data.message_id)
    if "Thursday" in message.content:
        raid = "thursday"
    elif "Saturday" in message.content:
        raid = "saturday"
    elif "Sunday" in message.content:
        raid = "sunday"

    member = await message.guild.query_members(user_ids=[data.user_id])
    member = member[0] or None
    if member != None:
        await tarChannel.send(
            "<:pepeexit:1110961845986148492> **"
            + member.display_name
            + "** unsigned from "
            + raid
            + "'s raid... RIP"
        )
    else:
        await tarChannel.send(
            "Someone unsigned from " + raid + "'s raid, sadly i don't remember who..."
        )


@client.event
async def on_raw_reaction_add(data):
    guild = client.get_guild(data.guild_id)
    ctxChannel = guild.get_channel(data.channel_id)
    tarChannel = discord.utils.get(guild.channels, id=CHANNEL_ID_UNSIGN)

    print("Someone just added reaction")

    raid = "SADPEPE"
    message = await ctxChannel.fetch_message(data.message_id)
    if "Thursday" in message.content:
        raid = "thursday"
    elif "Saturday" in message.content:
        raid = "saturday"
    elif "Sunday" in message.content:
        raid = "sunday"

    member = await message.guild.query_members(user_ids=[data.user_id])
    member = member[0] or None
    if member != None:
        await tarChannel.send(
            "**" + member.display_name + "** signed up for " + raid + "'s raid!"
        )
    else:
        await tarChannel.send(
            "Someone signed up for " + raid + "'s raid, sadly i don't know who..."
        )


client.run(key)
