from discord.ext import commands, tasks
from utils.emojis import *
import topgg
from dotenv import load_dotenv
import os

load_dotenv()
environment = os.getenv("ENVIRONMENT")
guildid = os.getenv("CUSTOM_GUILD")
dbl_token = os.getenv("DBL_TOKEN")


class Topgg(commands.Cog):
    def __init__(self, client):
        self.client = client

        self.client.topggpy = topgg.DBLClient(self.client, dbl_token)
        self.update_stats.start()

    @tasks.loop(minutes=30)
    async def update_stats(self):
        if environment == "custom":
            return
        try:
            await self.client.topggpy.post_guild_count()
            print(f"[🔝] Posted server count ({self.client.topggpy.guild_count})")
        except Exception as e:
            print("[⬇️] Failed to post server count")


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Topgg(client))
