import discord
import os
import random
import logging as log

from reaction_timeout import ReactionTimeout

from dotenv import load_dotenv
from datetime import timedelta
from discord.ext import tasks, commands
from discord import Forbidden

load_dotenv()
key = os.environ["TOKEN"]

CHANNEL_ID_GENERAL = 970095404031033374
CHANNEL_ID_UNSIGN = 1118182973037092884
CHANNEL_ID_SIGNIN = 982296021746978856

LOW = 19
HIGH = 25

MAX_OFFENSES = 3
OFFENSES_TIMEOUT = 60
PRISON_TIMEOUT = 120

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.moderation = True

client = discord.Client(intents=intents)
watcher = {}

FORMAT = "[%(asctime)s] (%(levelname)s): %(message)s"
log.basicConfig(level=log.INFO, format=FORMAT, datefmt="%m/%d/%Y %I:%M:%S %p")


@client.event
async def on_ready():
    log.info(f"We have logged in as {client.user}")


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

    # we only want to watch the sign-in-raids channel
    if ctxChannel.id != CHANNEL_ID_SIGNIN:
        return

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
        log.info(f"{member.display_name} just removed reaction for {raid}")
        await tarChannel.send(
            "<:pepeexit:1110961845986148492> **"
            + member.display_name
            + "** unsigned from "
            + raid
            + "'s raid... RIP"
        )
    else:
        log.info(f"Someone just removed reaction for {raid}")
        await tarChannel.send(
            "Someone unsigned from " + raid + "'s raid, sadly i don't remember who..."
        )

    if member != None:
        ban = await police_check(member)
        if ban:
            return
        else:
            await motivation_check(data, False, raid, member)


@client.event
async def on_raw_reaction_add(data):
    guild = client.get_guild(data.guild_id)
    ctxChannel = guild.get_channel(data.channel_id)
    tarChannel = discord.utils.get(guild.channels, id=CHANNEL_ID_UNSIGN)

    # we only want to watch the sign-in-raids channel
    if ctxChannel.id != CHANNEL_ID_SIGNIN:
        return

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
        log.info(f"{member.display_name} just added reaction for {raid}")
        await tarChannel.send(
            "**" + member.display_name + "** signed up for " + raid + "'s raid!"
        )
    else:
        log.info(f"Someone just added reaction for {raid}")
        await tarChannel.send(
            "Someone signed up for " + raid + "'s raid, sadly i don't know who..."
        )

    if member != None:
        ban = await police_check(member)
        if ban:
            return
        else:
            await motivation_check(data, True, raid, member)


def remove_reactionTimeout(member_id):
    log.info(f"user {member_id} reaction watcher refreshed")
    watcher.pop(member_id)


async def police_check(member):
    if member.id not in watcher:
        watcher[member.id] = ReactionTimeout(client, member.id, remove_reactionTimeout)
    else:
        watcher[member.id].increment()
        if watcher[member.id].count >= MAX_OFFENSES:
            log.info(f"user {member.id} sent to prison")
            try:
                await send_to_prison(member)
            except Forbidden as e:
                if e.code == 50013:
                    log.warning(f"insufficient permissions to timeout user {member.id}")
            finally:
                watcher[member.id].stop_watching()
                watcher.pop(member.id)

    return member.id not in watcher


async def send_to_prison(member):
    if member != None:
        log.info(f"user {member.display_name} sent to prison")
        await member.timeout(
            timedelta(seconds=PRISON_TIMEOUT),
            reason="Please do not spam the raid signup reactions!",
        )
        # if member.timed_out_until != None:
        await discord.utils.get(member.guild.channels, id=CHANNEL_ID_UNSIGN).send(
            "Busted! I have just sent **"
            + member.display_name
            + "** to prison for **"
            + str(PRISON_TIMEOUT)
            + " seconds**, for disrupting the peace in the #sign-in-raids channel! Trolls beware."
        )


async def motivation_check(
    reaction_data,
    reaction_type: bool,
    reaction_raid: str,
    member,
    channel_id: int = CHANNEL_ID_GENERAL,
):
    """Checks if the number of signsup has changed to match the LOW or HIGH env variables,
    if so, sends a motivational response to the supplied channel."""
    sizes = {LOW: "low", HIGH: "high"}

    answers_signup = {
        "low": [
            "Here we go! {_amount} signups already for **{_raid}**'s raid! Keep 'em coming!",
            "Oh yeah, {_amount} signups for **{_raid}**'s raid! Need more to go",
            "Great news! We've reached {_amount} signups for **{_raid}**! The raid is filling up fast!",
            "We're halfway there! {_amount} brave souls have signed up for **{_raid}**'s raid!",
            "{_amount} warriors have joined the cause! **{_raid}**'s raid is gaining momentum!",
            "Fantastic! We've hit the {_amount} signups mark for **{_raid}**'s raid!",
            "A round of applause for the {_amount} warriors ready to conquer **{_raid}**!",
            "It's a solid start! We've got {_amount} signups for **{_raid}**'s raid!",
            "We've reached {_amount} signups! **{_raid}**'s raid is shaping up nicely!",
            "So far,{_amount} brave adventurers have answered the call for **{_raid}**'s raid!",
        ],
        "high": [
            "Ladies and gentlemen, we have ourselves a raid on **{_raid}**! {_amount} people ready to parse!",
            "Woohoo! We've hit the {_amount} signups milestone for **{_raid}**'s raid!",
            "Breaking news! **{_raid}**'s raid now boasts an impressive count of {_amount} signups!",
            "A tremendous achievement! **{_raid}**'s raid has secured {_amount} brave participants!",
            "The word is spreading! {_amount} warriors have signed up for **{_raid}**'s raid!",
            "Incredible! We've reached {_amount} signups for **{_raid}**'s raid!",
            "Give a warm welcome to the {_amount} adventurers ready to tackle **{_raid}**!",
            "The hype is real! **{_raid}**'s raid has attracted {_amount} dedicated heroes!",
            "We've hit the jackpot! **{_raid}**'s raid now has {_amount} confirmed participants!",
            "**{_raid}**'s raid just crossed the {_amount} signups mark! Prepare for epic battles!",
        ],
    }

    answers_unsign = {
        "low": [
            "Oops! We just lost a signup for **{_raid}**'s raid. We're now down to {_amount} signups. Hang in there, {_user}!",
            "One brave soul, {_user}, had to back out from **{_raid}**'s raid. We currently have {_amount} signups. We'll miss you, {_user}!",
            "Unfortunately, {_user} had to cancel their signup for **{_raid}**'s raid. We're now at {_amount} signups.",
            "We're down to {_amount} signups for **{_raid}**'s raid as {_user} had to unsign. We hope to see you next time, {_user}!",
            "A warrior, {_user}, has withdrawn from **{_raid}**'s raid, leaving us with {_amount} signups. Farewell, {_user}!",
            "Regrettably, our count for **{_raid}**'s raid dropped to {_amount} as {_user} unsigned. We'll miss you, {_user}!",
            "We've had an unsigning for **{_raid}**'s raid. We're now left with {_amount} brave adventurers. Take care, {_user}!",
            "One spot just opened up as {_user} unsigned for **{_raid}**'s raid. We're at {_amount} signups. Farewell, {_user}!",
            "We've encountered a setback as {_user} had to unsign for **{_raid}**'s raid. We're down to {_amount} signups. Sorry, {_user}!",
            "A change of plans for {_user} has brought our count to {_amount} signups for **{_raid}**'s raid. Take care, {_user}!",
        ],
        "high": [
            "We received unfortunate news as {_user} unsigned for **{_raid}**'s raid. We're now at {_amount} signups. Hang in there, {_user}!",
            "A participant, {_user}, had to cancel their signup for **{_raid}**'s raid. We're down to {_amount} signups. We'll miss you, {_user}!",
            "It's disappointing to announce that our count for **{_raid}**'s raid decreased to {_amount} as {_user} unsigned. Sorry to see you go, {_user}!",
            "We've had a setback as {_user} had to unsign for **{_raid}**'s raid. We're now at {_amount} signups. Farewell, {_user}!",
            "Regrettably, a warrior had to withdraw from **{_raid}**'s raid. We're left with {_amount} signups. Take care, {_user}!",
            "We're at {_amount} signups for **{_raid}**'s raid as {_user} had to unsign. We'll miss you, {_user}!",
            "One participant just unsigned for **{_raid}**'s raid, leaving us with {_amount} brave adventurers. Farewell, {_user}!",
            "We've experienced a cancellation as {_user} had to unsign for **{_raid}**'s raid. We're at {_amount} signups. Take care, {_user}!",
            "We've encountered a change in our lineup as {_user} unsigned for **{_raid}**'s raid. We're down to {_amount} signups. Sorry, {_user}!",
            "Unfortunately, our count dropped to {_amount} signups for **{_raid}**'s raid due to an unsigning. Take care, {_user}!",
        ],
    }

    channel = client.get_channel(reaction_data.channel_id)
    message = await channel.fetch_message(reaction_data.message_id)
    reaction = discord.utils.get(message.reactions, emoji=reaction_data.emoji.name)

    if reaction_type == True and reaction and reaction.count in sizes.keys():
        await client.get_channel(channel_id).send(
            answers_signup[sizes[reaction.count]][
                random.randint(0, len(answers_signup[sizes[reaction.count]]) - 1)
            ].format(_amount=reaction.count, _raid=reaction_raid)
        )

    if reaction_type == False and reaction and reaction.count + 1 in sizes.keys():
        await client.get_channel(channel_id).send(
            answers_unsign[sizes[reaction.count + 1]][
                random.randint(0, len(answers_unsign[sizes[reaction.count + 1]]) - 1)
            ].format(
                _amount=reaction.count, _raid=reaction_raid, _user=member.display_name
            )
        )


client.run(key)
