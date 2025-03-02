from discord.ext import commands, tasks
import os

import datetime
from dotenv import load_dotenv
from datetime import datetime
from bson import ObjectId
from utils.emojis import *
import discord

load_dotenv()
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")


class Shed(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.check_scheduled_loas.start()
        print("[✅] LOA loop started")

    @tasks.loop(minutes=3, reconnect=True)
    async def check_scheduled_loas(self):
        print("[👀] Checking Scheduled LOAs")
        if self.client.loa_maintenance is True:
            return

        try:
            current_time = datetime.now()
            filter = {
                "guild_id": {"$exists": True},
                "scheduled": True,
                "start_time": {"$lte": current_time},
            }

            if environment == "custom":
                filter["guild_id"] = int(guildid)

            loa_requests = await self.client.db['loa'].find(filter).to_list(length=None)
            for request in loa_requests:
                start_time = request["start_time"]
                end_time = request["end_time"]
                UserID = request["user"]
                guild_id = request["guild_id"]
                guild = self.client.get_guild(guild_id)

                try:
                    user = await self.client.fetch_user(int(UserID))
                except (discord.NotFound, discord.HTTPException):
                    continue

                if not guild or not user:
                    await self.client.db['loa'].delete_one(
                        {"guild_id": guild_id, "user": UserID, "start_time": start_time}
                    )
                    continue

                Config = await self.client.config.find_one({"_id": guild_id})
                if not Config or not Config.get("LOA"):
                    continue

                channel_id = Config.get("LOA", {}).get("channel")
                if not isinstance(channel_id, int):
                    continue

                try:
                    channel = await guild.fetch_channel(channel_id)
                except (discord.NotFound, discord.HTTPException):
                    continue

                if current_time >= start_time:
                    role_id = Config.get("LOA", {}).get("role")
                    role = discord.utils.get(guild.roles, id=role_id)
                    if role:
                        request = await self.client.db['loa'].update_one(
                            {"_id": ObjectId(request.get("_id"))},
                            {"$set": {"active": True, "scheduled": False}},
                        )
                        if not request.modified_count == 1:
                            continue
                        try:
                            member = await guild.fetch_member(user.id)
                            await member.add_roles(role)
                            await member.send(
                                embed=discord.Embed(
                                    color=discord.Color.green(),
                                ).set_author(
                                    name=f"Your planned LOA @{guild.name} has started.",
                                    icon_url=user.display_avatar,
                                )
                            )
                        except discord.Forbidden:
                            print(f"[LOA] Failed to add role for {UserID}.")

        except Exception as e:
            print(f"[⚠️] Error in scheduled LOA task: {e}")
        del loa_requests
async def setup(client: commands.Bot) -> None:
    await client.add_cog(Shed(client))
