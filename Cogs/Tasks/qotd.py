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
from motor.motor_asyncio import AsyncIOMotorClient
import gc

MONGO_URL = os.getenv("MONGO_URL")
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")

client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]
questiondb = db["qotd"]
questionsa = db["Question Database"]


class qotd(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    async def fetch_question(self, used_questions, server: discord.Guild):
        questionresult = await questionsa.find({}).to_list(length=None)
        Unusued = [q for q in questionresult if q["question"] not in used_questions]

        if not Unusued:
            await questiondb.update_one(
                {"guild_id": server.id}, {"$set": {"messages": []}}
            )
            return random.choice(questionresult).get("question")
        del questionresult
        return random.choice(Unusued).get("question")

    @tasks.loop(minutes=15, reconnect=True)
    async def sendqotd(self) -> None:
        print("[👀] Checking QOTD")
        if environment == "custom":

            result = await questiondb.find({"guild_id": int(guildid)}).to_list(
                length=None
            )

        else:
            result = await questiondb.find({}).to_list(length=None)

        if not result:
            logging.critical(
                f"---------------------------------------------------------------------------------------"
            )
            logging.critical(
                f"                           [ FATAL ERROR QOTD RESULT IS NONE]                          "
            )
            logging.critical(
                f"---------------------------------------------------------------------------------------"
            )
            return

        for results in result:
            await asyncio.sleep(3)
            postdate = results.get("nextdate", None)
            if postdate is None:
                continue
            if not await ModuleCheck(results.get("guild_id"), "QOTD"):
                continue
            if postdate <= datetime.datetime.utcnow():
                messages = []
                messages = results.get("messages", [])
                try:
                    guild = await self.client.fetch_guild(
                        int(results.get("guild_id", None))
                    )
                except:
                    guild = None
                if guild is None:
                    continue

                question = await self.fetch_question(messages, guild)
                if question:
                    messages.append(question)

                ChannelID = results.get("channel_id", None)
                if ChannelID is None:
                    continue
                ChannelID = int(ChannelID)
                try:
                    channel = await guild.fetch_channel(ChannelID)
                except Exception as e:
                    channel = None
                if channel is None:
                    continue

                pingmsg = (
                    f"<@&{results.get('pingrole')}>" if results.get("pingrole") else ""
                )
                embed = discord.Embed(
                    title="<:Tip:1223062864793702431> Question of the Day",
                    description=f"{question}",
                    color=discord.Color.yellow(),
                    timestamp=datetime.datetime.utcnow(),
                )
                if not results.get("day"):
                    day = len(messages)
                else:
                    day = results.get("day") + 1
                embed.set_footer(
                    text=f"Day #{day}",
                    icon_url="https://cdn.discordapp.com/emojis/1231270156647403630.webp?size=96&quality=lossless",
                )
                logging.info(f"[👀] Sending QOTD for {guild.name} (ID: {guild.id})")
                try:
                    msg = await channel.send(
                        content=pingmsg,
                        embed=embed,
                        allowed_mentions=discord.AllowedMentions(roles=True),
                    )
                except Exception as e:
                    continue
                try:
                    await questiondb.update_one(
                        {"guild_id": int(results["guild_id"])},
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
                except Exception as e:
                    logging.warn(
                        f"{guild.name}(ID: {guild.id}) failed to update QOTD. {e}"
                    )
                    continue
                if results.get("qotdthread") is True:
                    try:
                        await msg.create_thread(name="QOTD Discussion")
                    except Exception as e:
                        continue
            

    @commands.Cog.listener()
    async def on_ready(self):
        self.sendqotd.start()


async def setup(client: commands.Bot) -> None:
    await client.add_cog(qotd(client))
