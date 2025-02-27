from discord.ext import commands, tasks
import os
import datetime
from discord.ext import tasks
from dotenv import load_dotenv
import os
from datetime import datetime
from utils.emojis import *
import discord
from discord.ext import tasks


load_dotenv()
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")



class LOA(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.check_loa_status.start()
        print("[✅] LOA loop started")

    @tasks.loop(minutes=3, reconnect=True)
    async def check_loa_status(self):
        print("[👀] Checking LOA Status")
        if self.client.loa_maintenance is True:
            return

        try:
            current_time = datetime.now()
            filter = {"active": True, "end_time": {"$lte": current_time}}

            if environment == "custom":
                filter = {
                    "guild_id": int(guildid),
                    "active": True,
                    "end_time": {"$lte": current_time},
                }

            loa_requests = await self.client.db['loa'].find(filter).to_list(length=None)
            for request in loa_requests:
                EndTime = request["end_time"]
                UserID = request["user"]
                guild_id = request["guild_id"]
                guild = self.client.get_guild(guild_id)

                try:
                    user = await self.client.fetch_user(int(UserID))
                except (discord.NotFound, discord.HTTPException):
                    continue

                if not guild or not user:
                    await self.client.db['loa'].delete_one(
                        {"guild_id": guild_id, "user": UserID, "end_time": EndTime}
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
                if current_time >= EndTime:
                    print(f"[LOA TASK] @{user.name}'s LOA has ended.")
                    await self.client.db['loa'].update_many(
                        {"guild_id": guild_id, "user": UserID},
                        {"$set": {"active": False}},
                    )
                    try:
                        embed = discord.Embed(
                            title="LOA Ended",
                            description=f"* **User:** {user.mention}\n* **Start Date:** <t:{int(request['start_time'].timestamp())}:f>\n* **End Date:** <t:{int(EndTime.timestamp())}:f>\n* **Reason:** {request['reason']}",
                            color=discord.Color.dark_embed(),
                        )
                        embed.set_author(
                            icon_url=user.display_avatar, name=user.display_name
                        )
                        await channel.send(embed=embed)
                    except discord.Forbidden:
                        print(f"[⚠️] Failed to send message to channel {channel_id}.")
                    finally:
                        role_id = Config.get("LOA", {}).get("role")
                        if role_id:
                            role = discord.utils.get(guild.roles, id=role_id)
                            if role:
                                try:
                                    member = await guild.fetch_member(user.id)
                                    await member.remove_roles(role)
                                except discord.Forbidden:
                                    print(f"[⚠️] Failed to remove role from {UserID}.")
                        try:
                            loanotification = await self.client.db['consent'].find_one(
                                {"user_id": user.id}
                            )
                            if (
                                loanotification
                                and loanotification.get("LOAAlerts", "Enabled")
                                == "Enabled"
                            ):
                                await user.send(
                                    embed=discord.Embed(
                                        color=discord.Color.brand_red(),
                                    ).set_author(
                                        name=f"Your LOA @{guild.name} has ended.",
                                        icon_url=user.display_avatar,
                                    )
                                )
                        except Exception as e:
                            print(f"[⚠️] Failed to send DM to {UserID}: {e}")

        except Exception as e:
            print(f"[⚠️] Error in LOA task: {e}")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(LOA(client))
