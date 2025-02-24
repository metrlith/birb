from discord.ext import commands
import os
import discord
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from discord.ext import tasks
from dotenv import load_dotenv
import os


MONGO_URL = os.getenv("MONGO_URL")
load_dotenv()
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")
# client = AsyncIOMotorClient(MONGO_URL)
# db = client["astro"]
# collection = db["infractions"]
# loa_collection = db["loa"]
# infractiontypeactions = db["infractiontypeactions"]
# config = db["Config"]



class expiration(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.check_infractions.start()
        print("[✅] Infraction Expiration loop started")

    @tasks.loop(minutes=30, reconnect=True)
    async def check_infractions(self):
        try:
            if self.client.infractions_maintenance is True:
             return            
            infractions = await self.client.db['infractions'].find(
                {"expiration": {"$exists": True}, "voided": {"$ne": True}}
            ).to_list(length=None)
            if environment == "custom":
                infractions = await self.client.db['infractions'].find(
                    {
                        "expiration": {"$exists": True},
                        "guild_id": int(guildid),
                        "expired": {"$ne": True},
                    }
                ).to_list(length=None)
            if infractions:
                for infraction in infractions:

                    if infraction.get("expired", False) is True:
                        continue
                    try:
                        guild = await self.client.fetch_guild(infraction["guild_id"])
                    except:
                        guild = None
                    if guild is None:
                        if not environment == "custom":
                            continue

                    Config = await self.client.config.find_one({"_id": guild.id})
                    if not Config:
                        continue
                    if not Config.get("Infraction", None):
                        continue
                    if not Config.get("Infraction", {}).get("channel"):
                        continue
                    if not Config.get('Infraction', {}).get('types', None):
                        continue
                    typechannel = None
                    infractiontype = infraction.get("action", None)
                    
                    if infractiontype:
                        infractionaction = await self.client.db['infractiontypeactions'].find_one(
                            {"name": infraction.get("action"), "guild_id": guild.id}
                        )
                        if infractionaction and infractionaction.get("channel_id"):
                            typechannel = self.client.get_channel(
                                infractionaction["channel_id"]
                            )
                    if infraction.get("expiration") is None:
                        continue
                    if infraction["expiration"] < datetime.now() and not infraction.get(
                        "expired", False
                    ):
                        await self.client.db['infractions'].update_one(
                            {"random_string": infraction["random_string"]},
                            {"$set": {"expired": True}},
                        )
                        print(
                            f"[✅] Updated expired infraction with ID: {infraction['random_string']}"
                        )

                        if infraction.get("msg_id") is not None:
                            if typechannel:
                                Channel = typechannel
                            else:
                                Config = await self.client.config.find_one({"_id": guild.id})
                                if Config:
                                    if not Config.get("Infraction", None):
                                        return
                                    if not Config.get("Infraction", {}).get("channel"):
                                        return
                                    Channel = self.client.get_channel(
                                        int(Config.get("Infraction", {}).get("channel"))
                                    )

                            if Channel is None:
                                continue

                            if Channel:
                                msg = await Channel.fetch_message(infraction["msg_id"])
                                if msg:
                                    await msg.reply(
                                        "<:CaseRemoved:1191901322723737600> Infraction has **expired**."
                                    )
                                    await msg.edit(
                                        content=f"{msg.content} • **Infraction Expired.**"
                                    )
                                    print(
                                        f"[✅] Updated expired infraction message with ID: {infraction.get('random_string')}"
                                    )

        except Exception as e:
            print(f"Error checking infractions: {e}")
async def setup(client: commands.Bot) -> None:
    await client.add_cog(expiration(client))
