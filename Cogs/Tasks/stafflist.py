import discord
from discord.ext import commands

from discord.ext import tasks
import os
from motor.motor_asyncio import AsyncIOMotorClient
import discord
from utils.emojis import *
from discord.ext import commands
from datetime import datetime
from utils.Module import ModuleCheck


MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]
stafflist = db["Staff List"]
activelists = db["Active Staff List"]
modules = db["Modules"]
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")


class StaffList(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.updatelist.start()
        print("[✅] Staff List loop started")


    @tasks.loop(minutes=10, reconnect=True)
    async def updatelist(self):
        print("Checking Staff List")
        if environment == "custom":
            activelistresult = await activelists.find(
                {"guild_id": int(guildid)}
            ).to_list(length=None)
        else:
            activelistresult = await activelists.find({}).to_list(length=None)

        if activelistresult:

            for data in activelistresult:
                try:

                    try:
                        guild = self.client.get_guild(data.get("guild_id", None))
                    except (discord.HTTPException, discord.NotFound):
                        continue
                    if not guild:
                        continue
                    if not await ModuleCheck(guild.id, "Staff List"):
                        continue

                    results = await stafflist.find({"guild_id": guild.id}).to_list(
                        length=None
                    )
                    if not results:
                        continue
                    results = sorted(results, key=lambda x: int(x.get("position", 0)))
                    member_roles = {}
                    highest_role_seen = {}
                    
                    if not guild.chunked:
                        await guild.chunk()
                    for member in guild.members:
                        highest_role = max(
                            (
                                role
                                for role in member.roles
                                if any(role.id == result["rank"] for result in results)
                            ),
                            key=lambda role: role.position,
                            default=None,
                        )
                        member_roles[member] = highest_role
                        highest_role_seen[member] = highest_role

                    embed = discord.Embed(
                        title="Staff Team",
                        color=discord.Color.dark_embed(),
                        timestamp=datetime.now(),
                    )
                    embed.set_thumbnail(url=guild.icon)
                    embed.set_author(name=guild.name, icon_url=guild.icon)
                    embed.set_footer(text="Last Updated")

                    description = ""
                    for result in results:
                        role = guild.get_role(result.get("rank"))
                        if role is not None:
                            members = [
                                member.mention
                                for member in member_roles
                                if member_roles[member] == role
                                and highest_role_seen[member] == role
                            ]
                            if members:
                                description += (
                                    f"### **{role.mention}** ({len(members)})\n\n> "
                                    + "\n> ".join(members)
                                    + "\n"
                                )
                            else:
                                continue
                        else:
                            continue
                    embed.description = description
                    ChannelsResult = data.get("channel_id")
                    msgresult = data.get("msg")
                    if ChannelsResult and msgresult:
                        try:
                            channel = await self.client.fetch_channel(ChannelsResult)
                        except (discord.HTTPException, discord.NotFound):
                            continue
                        if channel:
                            try:
                                msg = await channel.fetch_message(msgresult)
                                if not msg:
                                    continue
                                await msg.edit(
                                    embed=embed,
                                    allowed_mentions=discord.AllowedMentions().none(),
                                )
                            except (discord.HTTPException, discord.NotFound):
                                continue
                    else:
                        continue
                except Exception as e:
                    print(f"[ERROR] {e}")
                    continue

    @updatelist.before_loop
    async def before_updatelist(self):
        await self.client.wait_until_ready()

async def setup(client):
    await client.add_cog(StaffList(client))
