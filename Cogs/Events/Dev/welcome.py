import discord
from discord.ext import commands
from utils.emojis import *


class welcome(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member):
        target_guild_id = 1092976553752789054
        guild_on_join = self.client.get_guild(target_guild_id)

        if guild_on_join and member.guild.id == target_guild_id:
            channel_id = 1092976554541326372
            channel = guild_on_join.get_channel(channel_id)

            if channel:
                member_count = guild_on_join.member_count
                message = f"Welcome {member.mention} to **Astro Birb**! 👋"
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    style=discord.ButtonStyle.gray,
                    label=f"{member_count}",
                    disabled=True,
                ))
                view.add_item(discord.ui.Button(
                    label="Support",
                    url="https://canary.discord.com/channels/1092976553752789054/1328460590120702094",
                    style=discord.ButtonStyle.link,
                    emoji="<:link:1206670134064717904>",

                ))
                await channel.send(message, view=view)

async def setup(client: commands.Bot) -> None:
    await client.add_cog(welcome(client))
