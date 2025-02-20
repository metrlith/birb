import discord
from discord.ext import commands
import discord.http
import os
from utils.emojis import *
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv


load_dotenv()
Mongos = AsyncIOMotorClient(os.getenv("MONGO_URL"))
DB = Mongos["astro"]
Configuration = DB["Config"]


async def ModuleCheck(id, module: str):
    config = await Configuration.find_one({"_id": id})
    if config is None:
        config = {"_id": id, "Modules": {}}
    elif "Modules" not in config:
        config["Modules"] = {}

    if config["Modules"].get(module, False) is True:
        return True
    else:
        return False