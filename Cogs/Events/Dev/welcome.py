import discord
from discord.ext import commands
from utils.emojis import *
import os


class welcome(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if os.getenv("ENVIRONMENT") == "development":
            return

        guild_id, channel_id = 1092976553752789054, 1092976554541326372
        guild = self.client.get_guild(guild_id)

        if guild and member.guild.id == guild_id:
            channel = guild.get_channel(channel_id)
            if channel:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        style=discord.ButtonStyle.gray,
                        label=f"{guild.member_count}",
                        disabled=True,
                    )
                )
                view.add_item(
                    discord.ui.Button(
                        label="Support",
                        url="https://canary.discord.com/channels/1092976553752789054/1328460590120702094",
                        style=discord.ButtonStyle.link,
                        emoji="<:link:1206670134064717904>",
                    )
                )
                await channel.send(
                    f"Welcome {member.mention} to **Astro Birb**! 👋", view=view
                )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(welcome(client))
