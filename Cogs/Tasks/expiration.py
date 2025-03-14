from discord.ext import commands
import os
import discord

from datetime import datetime
from discord.ext import tasks
from dotenv import load_dotenv


load_dotenv()
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")


class expiration(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.CheckInfractions.start()
        print("[✅] Infraction Expiration loop started")

    @tasks.loop(minutes=30, reconnect=True)
    async def CheckInfractions(self):
        if self.client.infractions_maintenance:
            return

        filter = {
            "expiration": {"$lte": datetime.utcnow()},
            "expired": {"$exists": False},
        }
        if environment == "custom":
            filter = {
                "guild_id": int(guildid),
                "expiration": {"$lte": datetime.utcnow()},
                "expired": {"$exists": False},
            }
        infractions = (
            await self.client.db["infractions"].find(filter).to_list(length=None)
        )

        print(infractions)
        if not infractions:
            return
        for infraction in infractions:
            if not infraction.get("expiration"):
                continue
            if infraction.get("expiration") <= datetime.utcnow():
                ActionType = await self.client.db["infractiontypeactions"].find_one(
                    {
                        "name": infraction.get("type"),
                        "guild_id": infraction.get("guild_id"),
                    }
                )
                if ActionType and ActionType.get("channel"):
                    Channel = self.client.get_channel(ActionType.get("channel"))
                else:
                    Config = await self.client.config.find_one(
                        {"_id": infraction.get("guild_id")}
                    )
                    if not Config:
                        return
                    if not Config.get("Infraction", {}).get("channel", None):
                        return

                    Channel = self.client.get_channel(
                        int(Config.get("Infraction", {}).get("channel"))
                    )
                if not Channel:
                    continue
                try:
                    message = await Channel.fetch_message(infraction.get("msg_id"))
                    if not message:
                        continue
                    embed = message.embeds[0]
                    exp = discord.Embed(
                        color=discord.Color.orange(),
                    ).set_author(
                        name="Infraction Expired",
                        icon_url="https://cdn.discordapp.com/emojis/1345821183328784506.webp?size=96",
                    )
                    await message.edit(
                        embeds=[embed, exp],
                    )
                    staff = self.client.get_user(int(infraction.get("staff")))
                    if staff:
                        exp.timestamp = discord.utils.utcnow()
                        exp.add_field(
                            name="Details",
                            value=f"> **Action:** {infraction.get('action')}\n> **Reason:** {infraction.get('reason')}",
                        )
                        exp.set_footer(text=f"ID: {infraction.get('random_string')}")
                        await staff.send(embed=exp)

                except (discord.HTTPException, discord.NotFound):
                    pass
                await self.client.db["Infractions"].update_one(
                    {"_id": infraction.get("_id")}, {"$set": {"expired": True}}
                )

                del infraction
        del infractions


async def setup(client: commands.Bot) -> None:
    await client.add_cog(expiration(client))
