from discord.ext import commands, tasks
import os

import asyncio
import datetime
from datetime import datetime
from bson import ObjectId
from utils.emojis import *
import discord


async def TimeLeftz(loa: dict) -> int | str:
    if not loa or not loa.get("start_time") or not loa.get("end_time"):
        return "N/A"

    Added = 0
    if loa.get("AddedTime") is not None:
        if loa["AddedTime"].get("RequestExt") is not None:
            if loa["AddedTime"]["RequestExt"].get("status", "Rejected") == "Accepted":
                Added = int(loa["AddedTime"].get("Time", 0))
        else:
            Added = int(loa["AddedTime"].get("Time", 0))

    Removed = 0
    if loa.get("RemovedTime") is not None:
        Removed = int(loa["RemovedTime"].get("Duration", 0))
    return int(loa["end_time"].timestamp()) - int(datetime.utcnow().timestamp()) - (Removed - Added)



class Leave(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        self.LeaveExpiration.start()
        self.ScheduledLOA.start()
        print("[✅] Leave loops started")

    @tasks.loop(seconds=10)
    async def LeaveExpiration(self):
        LOAs = (
            await self.client.db["loa"]
            .find(
                {
                    "start_time": {"$exists": True},
                    "end_time": {"$exists": True},
                    "active": True,
                }
            )
            .to_list(length=None)
        )
        semaphore = asyncio.Semaphore(3)

        async def Process(L):
            async with semaphore:
                TimeLeft = await TimeLeftz(L)
                print(f"TimeLeft: {TimeLeft}")
                print(f"LOA: {L.get('_id')}")

                if TimeLeft in {None, "N/A"}:
                    return
                if TimeLeft <= 0:
                    print('hi')
                    await self.client.db["loa"].update_one(
                        {"_id": ObjectId(L["_id"])}, {"$set": {"active": False}}
                    )
                    self.client.dispatch("leave_end", L.get("_id"))

        await asyncio.gather(*(Process(L) for L in LOAs))

    @tasks.loop(seconds=10)
    async def ScheduledLOA(self):
        LOAs = (
            await self.client.db["loa"]
            .find(
                {
                    "start_time": {"$exists": True},
                    "end_time": {"$exists": True},
                    "scheduled": True,
                    "active": False,
                    "request": False,
                }
            )
            .to_list(length=None)
        )
        semaphore = asyncio.Semaphore(3)

        async def Process(L):
            async with semaphore:
                if not L.get("start_time"):
                    return
                if int(datetime.utcnow().timestamp()) >= int(
                    L.get("start_time").timestamp()
                ):
                    await self.client.db["loa"].update_one(
                        {"_id": ObjectId(L["_id"])},
                        {"$set": {"active": True, "scheduled": False}},
                    )
                    self.client.dispatch("leave_start", L.get("_id"))

        await asyncio.gather(*(Process(L) for L in LOAs))


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Leave(client))
