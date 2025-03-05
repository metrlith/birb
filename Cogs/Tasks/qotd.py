import os
import discord
from discord.ext import commands, tasks
import datetime
from utils.emojis import *
import random
from dotenv import load_dotenv

load_dotenv()
import asyncio
import logging
from utils.Module import ModuleCheck

MONGO_URL = os.getenv("MONGO_URL")
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")

import asyncio


class qotd(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.semaphore = asyncio.Semaphore(10)

    async def fetch_question(self, used_questions, server: discord.Guild):
        questionresult = (
            await self.client.db["Question Database"].find({}).to_list(length=None)
        )
        Unusued = [q for q in questionresult if q["question"] not in used_questions]

        if not Unusued:
            await self.client.db["qotd"].update_one(
                {"guild_id": server.id}, {"$set": {"messages": []}}
            )
            return random.choice(questionresult).get("question")
        del questionresult
        return random.choice(Unusued).get("question")

    async def ProcesssQOTD(self, results):
        async with self.semaphore:
            try:
                postdate = results.get("nextdate", None)
                if postdate is None or postdate > datetime.datetime.utcnow():
                    return

                guild_id = int(results.get("guild_id"))
                guild = await self.client.fetch_guild(guild_id)
                if guild is None:
                    return

                messages = results.get("messages", [])
                question = await self.fetch_question(messages, guild)
                if question:
                    messages.append(question)

                ChannelID = results.get("channel_id", None)
                if ChannelID is None:
                    return
                ChannelID = int(ChannelID)
                try:
                    channel = await guild.fetch_channel(ChannelID)
                except Exception:
                    return

                pingmsg = (
                    f"<@&{results.get('pingrole')}>" if results.get("pingrole") else ""
                )
                embed = discord.Embed(
                    title="<:Tip:1223062864793702431> Question of the Day",
                    description=f"{question}",
                    color=discord.Color.yellow(),
                    timestamp=datetime.datetime.utcnow(),
                )

                day = results.get("day", 0) + 1
                embed.set_footer(
                    text=f"Day #{day}",
                    icon_url="https://cdn.discordapp.com/emojis/1231270156647403630.webp?size=96&quality=lossless",
                )

                msg = await channel.send(
                    content=pingmsg,
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=True),
                )

                await self.client.db["qotd"].update_one(
                    {"guild_id": guild_id},
                    {
                        "$set": {
                            "nextdate": datetime.datetime.utcnow()
                            + datetime.timedelta(days=1),
                            "messages": messages,
                            "day": day,
                        }
                    },
                    upsert=True,
                )

                if results.get("qotdthread"):
                    await msg.create_thread(name="QOTD Discussion")

            except Exception as e:
                logging.warn(f"Error processing QOTD for guild {guild_id}: {e}")

    @tasks.loop(minutes=15, reconnect=True)
    async def sendqotd(self) -> None:
        print("[👀] Checking QOTD")
        result = None
        filter = {"nextdate": {"$lte": datetime.datetime.utcnow()}}
        if bool(environment == "custom"):
            filter["guild_id"] = int(guildid)
        if not result:
            return

        tasks = [self.ProcesssQOTD(results) for results in result]
        await asyncio.gather(*tasks)

    @commands.Cog.listener()
    async def on_ready(self):
        self.sendqotd.start()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(qotd(client))
