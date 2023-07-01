import discord
import os
import random
import logging as log
import sqlite3
import re

from reaction_timeout import ReactionTimeout
from dotenv import load_dotenv, set_key
from datetime import timedelta
from discord import Forbidden, app_commands

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

load_dotenv(override=True)
key = os.environ["TOKEN"]

_guild_test = discord.Object(id=1122548133717618808)

LOW = 1
HIGH = 2

MAX_OFFENSES = 4
OFFENSES_TIMEOUT = 60
PRISON_TIMEOUT = 120

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.moderation = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
watcher = {}

FORMAT = "[%(asctime)s] (%(levelname)s): %(message)s"
log.basicConfig(level=log.INFO, format=FORMAT, datefmt="%m/%d/%Y %I:%M:%S %p")


@tree.command(
    name="status",
    description="Returns basic info about the bot's presence on this server",
    # guild=_guild_test,
)
async def status(interaction):
    log.info(f"{interaction.user.display_name} used the 'Status' command")

    cursor.execute(
        f"""SELECT CT.name, C.channel_name 
            FROM channels C JOIN channels_types CT on C.channel_type = CT.id 
            WHERE guild_id = {interaction.guild_id}"""
    )
    result = ""
    for row in cursor.fetchall():
        result += str(row) + "\n"

    await interaction.response.send_message(
        "I am alive and well! \n" + result, ephemeral=True
    )


@tree.command(
    name="set_channel_announce",
    description="Specify Channel, where the bot will announce sign-up milestones for raids",
    # guild=_guild_test,
)
@app_commands.describe(channel="Channel to announce to")
async def set_channel_announce(interaction, channel: discord.TextChannel):
    log.info(
        f"{interaction.user.display_name} used the 'Set Channel Announce' command."
    )

    cursor.execute(
        "REPLACE INTO channels (guild_id, guild_name, channel_type, channel_id, channel_name) VALUES (?,?,?,?,?);",
        (interaction.guild_id, interaction.guild.name, 1, channel.id, channel.name),
    )
    conn.commit()

    await interaction.response.send_message(
        f"New channel for announcements: <#{channel.id}>", ephemeral=True
    )

    log.info(f"New channel for announcements: {channel.name}")


@tree.command(
    name="set_channel_report",
    description="Specify Channel, where the bot will report sign-in activity",
    # guild=_guild_test,
)
@app_commands.describe(channel="Channel to report to")
async def set_channel_report(interaction, channel: discord.TextChannel):
    log.info(f"{interaction.user.display_name} used the 'Set Channel Report' command.")

    cursor.execute(
        "REPLACE INTO channels (guild_id, guild_name, channel_type, channel_id, channel_name) VALUES (?,?,?,?,?);",
        (interaction.guild_id, interaction.guild.name, 2, channel.id, channel.name),
    )
    conn.commit()

    await interaction.response.send_message(
        f"New channel for reporting sign-in activity: <#{channel.id}>", ephemeral=True
    )

    log.info(f"New channel for reports: {channel.name}")


@tree.command(
    name="set_channel_observe",
    description="Specify Channel, where the bot listen for reactions",
    # guild=_guild_test,
)
@app_commands.describe(channel="Channel to listen in")
async def set_channel_report(interaction, channel: discord.TextChannel):
    log.info(f"{interaction.user.display_name} used the 'Set Channel Observe' command.")

    cursor.execute(
        "REPLACE INTO channels (guild_id, guild_name, channel_type, channel_id, channel_name) VALUES (?,?,?,?,?);",
        (interaction.guild_id, interaction.guild.name, 3, channel.id, channel.name),
    )
    conn.commit()

    await interaction.response.send_message(
        f"New channel to listen for sign-in activity: <#{channel.id}>", ephemeral=True
    )

    log.info(f"New channel for observing: {channel.name}")


@client.event
async def on_ready():
    await tree.sync()
    log.info(f"We have logged in as {client.user}")


@client.event
async def on_raw_reaction_remove(data):
    guild = client.get_guild(data.guild_id)
    ctxChannel = guild.get_channel(data.channel_id)
    tarChannel = discord.utils.get(
        guild.channels,
        id=cursor.execute(
            f"""
                SELECT channel_id
                FROM channels
                WHERE channel_type = 2 AND guild_id = {guild.id}
            """
        ).fetchone()[0],
    )
    CHANNEL_OBSERVE_ID = cursor.execute(
        f"""
                SELECT channel_id
                FROM channels
                WHERE channel_type = 3 AND guild_id = {guild.id}
            """
    ).fetchone()[0]

    # we only want to watch the sign-in-raids channel
    if ctxChannel.id != CHANNEL_OBSERVE_ID:
        return

    message = await ctxChannel.fetch_message(data.message_id)

    match, day, raid, size, diff = parse_message(message.content)

    member = await message.guild.query_members(user_ids=[data.user_id])
    member = member[0] or None

    raid_complete = f"{day}'s {raid} {size} {diff}"

    if member != None:
        ban = await police_check(member)
        if ban:
            return
        else:
            if match:
                log.info(
                    f"{member.display_name} just removed reaction for {raid_complete}"
                )
                await tarChannel.send(
                    f"<:pepeexit:1110961845986148492> **{member.display_name}** unsigned from {raid_complete} raid!"
                )
            else:
                log.info(
                    f"{member.display_name} just removed reaction from a raid in a wrong format"
                )
                await tarChannel.send(
                    f"<:pepeexit:1110961845986148492> **{member.display_name}** unsigned from a raid! The raid message is in the wrong format, message server admins!"
                )
            await motivation_check(data, False, raid_complete, member, guild)
    else:
        log.info(f"Someone just removed reaction from {raid_complete}")
        await tarChannel.send(
            f"**Someone** unsigned from {raid_complete} raid, sadly i don't know who..."
        )


@client.event
async def on_raw_reaction_add(data):
    guild = client.get_guild(data.guild_id)
    ctxChannel = guild.get_channel(data.channel_id)
    tarChannel = discord.utils.get(
        guild.channels,
        id=cursor.execute(
            f"""
                SELECT channel_id
                FROM channels
                WHERE channel_type = 2 AND guild_id = {guild.id}
            """
        ).fetchone()[0],
    )
    CHANNEL_OBSERVE_ID = cursor.execute(
        f"""\
                SELECT channel_id
                FROM channels
                WHERE channel_type = 3 AND guild_id = {guild.id}
            """
    ).fetchone()[0]

    # we only want to watch the sign-in-raids channel
    if ctxChannel.id != CHANNEL_OBSERVE_ID:
        return

    message = await ctxChannel.fetch_message(data.message_id)

    match, day, raid, size, diff = parse_message(message.content)

    member = await message.guild.query_members(user_ids=[data.user_id])
    member = member[0] or None

    raid_complete = f"{day}'s {raid} {size} {diff}"

    if member != None:
        ban = await police_check(member)
        if ban:
            return
        else:
            if match:
                log.info(
                    f"{member.display_name} just added reaction for {raid_complete}"
                )
                await tarChannel.send(
                    f"**{member.display_name}** signed up for {raid_complete} raid!"
                )
            else:
                log.info(
                    f"{member.display_name} just added reaction for a raid in a wrong format"
                )
                await tarChannel.send(
                    f"**{member.display_name}** signed up for a raid! The raid message is in the wrong format, message server admins!"
                )
            await motivation_check(data, True, raid_complete, member, guild)
    else:
        log.info(f"Someone just added reaction for {raid_complete}")
        await tarChannel.send(
            f"**Someone** signed up for {raid_complete} raid, sadly i don't know who..."
        )


# regex pattern that matches {day} - {raid_name} {size} {difficulty} ({additional_info}) with the last group being optional *
def parse_message(content):
    content = content.replace("*", "")
    content = content.replace("~", "")
    content = content.replace("  ", " ")

    pattern = r"(?:.*\s)?((?:This\s|Next\s)?\w+) - (.+) (\d+) (\w+)( \(.+\))?.*"
    match = re.match(pattern, content)

    if match:
        groups = [group.strip() if group else group for group in match.groups()]
        day, raid, size, difficulty = groups[0], groups[1], groups[2], groups[3]
        return True, day, raid, size, difficulty
    else:
        return False, "day", "raid", "raidSize", "difficulty"


def remove_reactionTimeout(member_id):
    log.info(f"user {member_id} reaction watcher refreshed")
    watcher.pop(member_id)


async def police_check(member):
    if member.id not in watcher:
        watcher[member.id] = ReactionTimeout(client, member.id, remove_reactionTimeout)
    else:
        watcher[member.id].increment()
        if watcher[member.id].count >= MAX_OFFENSES:
            try:
                await send_to_prison(member)
            except Forbidden as e:
                if e.code == 50013:
                    log.warning(
                        f"insufficient permissions to timeout user {member.display_name}"
                    )
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

        cursor.execute(
            f"SELECT channel_id FROM channels WHERE channel_type = 2 AND guild_id = {member.guild.id}"
        )
        channel_id_report = cursor.fetchall()

        # if member.timed_out_until != None:
        await discord.utils.get(member.guild.channels, id=channel_id_report).send(
            "Busted! I have just sent **"
            + member.display_name
            + "** to prison for **"
            + str(PRISON_TIMEOUT)
            + " seconds**, for disrupting the peace in the #sign-in-raids channel! Trolls beware."
        )


async def motivation_check(
    reaction_data, reaction_type: bool, reaction_raid_complete: str, member, guild
):
    """Checks if the number of signsup has changed to match the LOW or HIGH env variables,
    if so, sends a motivational response to the supplied channel."""
    sizes = {LOW: "low", HIGH: "high"}
    channel_id = cursor.execute(
        f"""
                SELECT channel_id
                FROM channels
                WHERE channel_type = 1 AND guild_id = {guild.id}
            """
    ).fetchone()[0]

    answers_signup = {
        "low": [
            "Here we go! {_amount} signups already for **{_raid_complete}** raid! Keep 'em coming!",
            "Oh yeah, {_amount} signups for **{_raid_complete}** raid! Need more to go",
            "Great news! We've reached {_amount} signups for **{_raid_complete}**! The raid is filling up fast!",
            "We're halfway there! {_amount} brave souls have signed up for **{_raid_complete}** raid!",
            "{_amount} warriors have joined the cause! **{_raid_complete}** raid is gaining momentum!",
            "Fantastic! We've hit the {_amount} signups mark for **{_raid_complete}** raid!",
            "A round of applause for the {_amount} warriors ready to conquer **{_raid_complete}**!",
            "It's a solid start! We've got {_amount} signups for **{_raid_complete}** raid!",
            "We've reached {_amount} signups! **{_raid_complete}** raid is shaping up nicely!",
            "So far,{_amount} brave adventurers have answered the call for **{_raid_complete}** raid!",
        ],
        "high": [
            "Woohoo! We've hit the {_amount} signups milestone for **{_raid_complete}** raid!",
            "Breaking news! **{_raid_complete}**'s raid now boasts an impressive count of {_amount} signups!",
            "A tremendous achievement! **{_raid_complete}** raid has secured {_amount} brave participants!",
            "The word is spreading! {_amount} warriors have signed up for **{_raid_complete}** raid!",
            "Incredible! We've reached {_amount} signups for **{_raid_complete}** raid!",
            "Give a warm welcome to the {_amount} adventurers ready to tackle **{_raid_complete}**!",
            "The hype is real! **{_raid_complete}** raid has attracted {_amount} dedicated heroes!",
            "We've hit the jackpot! **{_raid_complete}** raid now has {_amount} confirmed participants!",
            "**{_raid_complete}** raid just crossed the {_amount} signups mark! Prepare for epic battles!",
        ],
    }

    answers_unsign = {
        "low": [
            "Oops! We just lost a signup for **{_raid_complete}** raid. We're now down to {_amount} signups. Hang in there, {_user}!",
            "One brave soul, {_user}, had to back out from **{_raid_complete}** raid. We currently have {_amount} signups. We'll miss you, {_user}!",
            "Unfortunately, {_user} had to cancel their signup for **{_raid_complete}** raid. We're now at {_amount} signups.",
            "We're down to {_amount} signups for **{_raid_complete}** raid as {_user} had to unsign. We hope to see you next time, {_user}!",
            "A warrior, {_user}, has withdrawn from **{_raid_complete}** raid, leaving us with {_amount} signups. Farewell, {_user}!",
            "Regrettably, our count for **{_raid_complete}** raid dropped to {_amount} as {_user} unsigned. We'll miss you, {_user}!",
            "We've had an unsigning from **{_raid_complete}** raid. We're now left with {_amount} brave adventurers. Take care, {_user}!",
            "One spot just opened up as {_user} unsigned from **{_raid_complete}** raid. We're at {_amount} signups. Farewell, {_user}!",
            "We've encountered a setback as {_user} had to unsign from **{_raid_complete}** raid. We're down to {_amount} signups. Sorry, {_user}!",
            "A change of plans for {_user} has brought our count to {_amount} signups for **{_raid_complete}** raid. Take care, {_user}!",
        ],
        "high": [
            "We received unfortunate news as {_user} unsigned from **{_raid_complete}** raid. We're now at {_amount} signups. Hang in there, {_user}!",
            "A participant, {_user}, had to cancel their signup for **{_raid_complete}** raid. We're down to {_amount} signups. We'll miss you, {_user}!",
            "It's disappointing to announce that our count for **{_raid_complete}** raid decreased to {_amount} as {_user} unsigned. Sorry to see you go, {_user}!",
            "We've had a setback as {_user} had to unsign from **{_raid_complete}** raid. We're now at {_amount} signups. Farewell, {_user}!",
            "Regrettably, a warrior had to withdraw from **{_raid_complete}** raid. We're left with {_amount} signups. Take care, {_user}!",
            "We're at {_amount} signups for **{_raid_complete}** raid as {_user} had to unsign. We'll miss you, {_user}!",
            "One participant just unsigned from **{_raid_complete}** raid, leaving us with {_amount} brave adventurers. Farewell, {_user}!",
            "We've experienced a cancellation as {_user} had to unsign from **{_raid_complete}** raid. We're at {_amount} signups. Take care, {_user}!",
            "We've encountered a change in our lineup as {_user} unsigned from **{_raid_complete}** raid. We're down to {_amount} signups. Sorry, {_user}!",
            "Unfortunately, our count dropped to {_amount} signups for **{_raid_complete}** raid due to an unsigning. Take care, {_user}!",
        ],
    }

    channel = client.get_channel(reaction_data.channel_id)
    message = await channel.fetch_message(reaction_data.message_id)
    reaction = discord.utils.get(message.reactions, emoji=reaction_data.emoji.name)

    if reaction_type == True and reaction and reaction.count in sizes.keys():
        await client.get_channel(channel_id).send(
            answers_signup[sizes[reaction.count]][
                random.randint(0, len(answers_signup[sizes[reaction.count]]) - 1)
            ].format(_amount=reaction.count, _raid_complete=reaction_raid_complete)
        )

    if reaction_type == False and reaction and reaction.count + 1 in sizes.keys():
        await client.get_channel(channel_id).send(
            answers_unsign[sizes[reaction.count + 1]][
                random.randint(0, len(answers_unsign[sizes[reaction.count + 1]]) - 1)
            ].format(
                _amount=reaction.count,
                _raid_complete=reaction_raid_complete,
                _user=member.display_name,
            )
        )


client.run(key)
