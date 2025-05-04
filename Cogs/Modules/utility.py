import discord
from discord.ext import commands, tasks
from discord import app_commands

from datetime import datetime
from typing import Optional


import aiohttp
from utils.emojis import *
from typing import Literal
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")
import numpy as np
from scipy.interpolate import CubicSpline


class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client
        client.launch_time = datetime.now()
        self.client.help_command = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.SavePing.start()

    @app_commands.command(description="View someones avatar")
    @app_commands.allowed_installs(guilds=False, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(self, interaction: discord.Interaction, user: discord.User = None):
        if user is None:
            user = interaction.user
        embed = discord.Embed(
            title=f"{(user.name).capitalize()}'s Avatar",
            color=discord.Color.dark_embed(),
        )
        embed.set_image(url=user.display_avatar)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="birb", description="Get silly birb photo")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def birb(self, interaction: discord.Interaction):
        try:
            async with aiohttp.ClientSession() as session, session.get(
                "https://api.alexflipnote.dev/birb"
            ) as response:
                response.raise_for_status()
                data = await response.json()

            embed = discord.Embed(color=discord.Color.dark_embed())
            embed.set_image(url=data.get("file"))
            await interaction.response.send_message(embed=embed)

        except aiohttp.ClientError as e:
            await interaction.response.send_message(
                f"{crisis} {interaction.user.mention}, I couldn't get a birb image for you :c\n**Error:** `{e}`",
            )

    async def Gen(self, data: dict) -> BytesIO:
        plt.style.use("dark_background")
        plt.figure(figsize=(10, 5))

        keys = ["Latency", "DB"]
        colors = {"Latency": "cyan", "DB": "green"}

        for key in keys:
            if key in data and data[key]:
                y = list(map(lambda x: float(x) if x != "N/A" else 0, data[key]))
                x = np.arange(len(y))

                cs = CubicSpline(x, y)

                x_new = np.linspace(x.min(), x.max(), 500)
                y_new = cs(x_new)

                plt.plot(
                    x_new,
                    y_new,
                    label=key,
                    color=colors[key],
                    linewidth=2,
                    linestyle="-",
                    alpha=0.8,
                )
                plt.fill_between(x_new, y_new, color=colors[key], alpha=0.2)

        plt.xticks([])
        plt.legend()
        plt.grid(alpha=0.2)
        plt.ylim(0, 400)  
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=100)
        buffer.seek(0)
        plt.close()
        return buffer

    async def DbConnection(self) -> str:
        try:
            await self.client.db.command("ping")
            return "Connected"
        except Exception:
            return "Not Connected"

    @tasks.loop(minutes=5)
    async def SavePing(self):
        Latency = (
            round(self.client.latency * 1000)
            if not np.isnan(self.client.latency)
            else 0
        )

        try:
            Start = datetime.now()
            await self.client.db.command("ping")
            DbLatency = (datetime.now() - Start).total_seconds() * 1000
            if DbLatency > 700:
                DbLatency = None
        except Exception:
            DbLatency = None

        await self.client.db["Ping"].update_one(
            {"_id": 0},
            {
                "$push": {
                    "Latency": {"$each": [str(Latency)], "$slice": -30},
                    "DB": {
                        "$each": [str(DbLatency) if DbLatency else "100"],
                        "$slice": -30,
                    },
                },
                "$setOnInsert": {"_id": 0},
            },
            upsert=True,
        )

    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        data = await self.client.db["Ping"].find_one({"_id": 0})
        await interaction.response.defer()
        graph = await self.Gen(data)
        file = discord.File(graph, filename="ping_graph.png")

        Dis = (
            round(self.client.latency * 1000)
            if not np.isnan(self.client.latency)
            else 0
        )
        try:
            Start = datetime.now()
            await self.client.db.command("ping")
            DbLatency = (datetime.now() - Start).total_seconds() * 1000
        except Exception:
            DbLatency = None
        embed = discord.Embed(color=discord.Color.dark_embed())
        embed.set_author(
            name=self.client.user.name, icon_url=self.client.user.display_avatar
        )
        embed.add_field(
            name="Status",
            value=f"> **Latency:** `{Dis} ms`\n> **Shard ({interaction.guild.shard_id}):** `{self.client.shards[interaction.guild.shard_id].latency * 1000:.0f} ms`\n> **Uptime:** <t:{int(self.client.launch_time.timestamp())}:R>",
            inline=False,
        )
        embed.add_field(
            name="Database",
            value=f"> **Database Latency:** `{round(DbLatency if DbLatency else 'N/A')} ms`\n> **Database Status:** `{await self.DbConnection()}`",
            inline=False,
        )
        embed.set_image(url="attachment://ping_graph.png")

        await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(description="Get support from the support server")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def support(self, interaction: discord.Interaction):
        view = Support()
        bot_user = self.client.user
        embed = discord.Embed(
            description="Encountering issues with Astro Birb? Our support team is here to help! Join our official support server using the link below.",
            color=0x2B2D31,
        )
        embed.set_author(name=bot_user.display_name, icon_url=bot_user.display_avatar)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(description="Invite Astro Birb to your server")
    @app_commands.allowed_installs(guilds=False, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def invite(self, interaction: discord.Interaction):
        view = invite()
        await interaction.response.send_message(view=view)

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:

        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


class invite(discord.ui.View):
    def __init__(self):
        super().__init__()
        url = "https://discord.com/api/oauth2/authorize?client_id=1113245569490616400&permissions=1632557853697&scope=bot%20applications.commands"
        self.add_item(
            discord.ui.Button(
                label="Invite",
                url=url,
                style=discord.ButtonStyle.blurple,
                emoji="<:link:1206670134064717904>",
            )
        )


class Support(discord.ui.View):
    def __init__(self):
        super().__init__()
        url = "https://discord.gg/DhWdgfh3hN"
        self.add_item(
            discord.ui.Button(
                label="Join",
                url=url,
                style=discord.ButtonStyle.blurple,
                emoji="<:link:1206670134064717904>",
            )
        )
        self.add_item(
            discord.ui.Button(
                label="Documentation",
                url="https://docs.astrobirb.dev",
                style=discord.ButtonStyle.blurple,
                emoji="📚",
            )
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Utility(client))
