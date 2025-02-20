import discord
from discord import app_commands
from discord.ext import commands
import platform
import psutil
import os
from motor.motor_asyncio import AsyncIOMotorClient
import string
import random
import datetime
from utils.emojis import *

from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]
T = db["Tickets"]


class Buttons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Support", style=discord.ButtonStyle.green, custom_id="TICKET:SUPPORT"
    )
    async def Support(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.OpenTicket(interaction, interaction.user, 0)

    async def OpenTicket(
        self, interaction: discord.Interaction, member: discord.Member, type: int
    ):
        t = await T.find_one({"UserID": member.id, "closed": None})
        if t:
            return await interaction.response.send_message(
                f"{no} **{member.display_name}**, you already have a ticket open! If this is a mistake contact a developer.",
                ephemeral=True,
            )
        await interaction.response.send_modal(Reason(type))


AllowedRoles = (
    1257815758977765558,
    1092977378638188594,
    1092977224501710848,
    1092977110412439583,
    1127223190616289430
)


class Tickets(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    async def AllowedRoles(self, member: discord.Member):
        for role in member.roles:
            if role.id in AllowedRoles:
                return True
        return False

    @commands.Cog.listener()
    async def on_ready(self):
        await self.RegisterCommands()
        print("[Tickets] Registering ticket commands")

    async def RegisterCommands(self):
        guild = discord.Object(id=1092976553752789054)
        Group = app_commands.Group(name="ticket", description="Manage tickets")

        Group.add_command(
            app_commands.Command(
                name="close", description="Close a ticket", callback=self.close
            )
        )
        Group.add_command(
            app_commands.Command(
                name="closerequest",
                description="Request to close the ticket.",
                callback=self.closerequest,
            )
        )
        Group.add_command(
            app_commands.Command(
                name="rename", description="Rename the ticket.", callback=self.rename
            )
        )

        self.client.tree.add_command(Group, guild=guild)
        await self.client.tree.sync(guild=guild)

    @commands.command()
    @commands.is_owner()
    async def panel(self, ctx: commands.Context):
        Divider = "<:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617><:line:1218542284040175617>"
        view = Buttons()
        await ctx.send(
            f"## 🌿 Birb Support\n{Divider}\n***You must only be opening this if:***\n` 1. ` You need help with the discord bot and the docs didn't help you.\n` 2. ` You've found a bug and you'd like to report it. (Developer Assistance)\n` 3. ` You would like to report a staff member. (Developer Assistance)\n## 🔗 Links\n{Divider}\n` Documentation ` • <https://docs.astrobirb.dev/>\n` Status ` • <https://status.astrobirb.dev/>\n` Website ` • <https://www.astrobirb.dev/>\n{Divider}",
            view=view,
        )

    async def rename(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer()
        if not await self.AllowedRoles(interaction.user):
            return await interaction.followup.send(
                content=f"{no} You don't have permission to use this command."
            )

        Result = await T.find_one({"channel": interaction.channel.id})
        if not Result:
            return await interaction.followup.send(content=f"{no} This isn't a ticket channel.")
        await T.update_one({"channel": interaction.channel.id}, {"$set": {"name": name}})
        await interaction.channel.edit(name=name)
        await interaction.followup.send(content=f"{tick} Successfully renamed ticket to {name}")

    async def close(self, interaction: discord.Interaction, reason: str = None):
        if not await self.AllowedRoles(interaction.user):
            return await interaction.response.send_message(
                f"{no} You don't have permission to use this command."
            )
        Result = await T.find_one({"channel": interaction.channel.id})
        if not Result:
            return await interaction.response.send_message(f"{no} This isn't a ticket channel.")
        await interaction.response.defer()
        self.client.dispatch("ticket_close", Result.get("_id"), reason, interaction.user)

    async def closerequest(self, interaction: discord.Interaction, reason: str = None):
        if not await self.AllowedRoles(interaction.user):
            return await interaction.user.send(
                f"{no} You don't have permission to use this command."
            )
        Result = await T.find_one({"channel": interaction.channel.id})
        if not Result:
            return await interaction.response.send_message(
                f"{no} This isn't a ticket channel."
            )
        embed = discord.Embed(
            title="Close Request",
            description=f"{interaction.user.mention}, is requesting to close the ticket.\n-# Click Confirm to close this ticket.",
            color=discord.Color.green(),
        )
        try:
            User = await interaction.guild.fetch_member(Result.get("UserID"))
        except (discord.NotFound, discord.HTTPException):
            return await interaction.response.send_message(
                f"{no} I can't find the user that opened this ticket."
            )

        await interaction.response.send_message(
            embed=embed, view=CloseRequest(User, reason), content=User.mention
        )


class CloseRequest(discord.ui.View):
    def __init__(self, member: discord.Member, reason: str):
        super().__init__(timeout=None)
        self.member = member
        self.reason = reason

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user != self.member:
            return await interaction.response.send_message(
                f"{no} You can't close this ticket.", ephemeral=True
            )
        await interaction.response.defer()
        Result = await T.find_one({"channel": interaction.channel.id})
        if not Result:
            return await interaction.followup.send(
                f"{no} This isn't a ticket channel.", ephemeral=True
            )
        await interaction.message.delete()
        interaction.client.dispatch(
            "ticket_close", Result.get("_id"), self.reason, interaction.user
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.member:
            return await interaction.response.send_message(
                f"{no} You can't close this ticket.", ephemeral=True
            )
        await interaction.response.edit_message(view=None, content=f"{no} Cancelled.")


class Reason(discord.ui.Modal):
    def __init__(self, type: int):
        super().__init__(title="Reason")
        self.reason = discord.ui.TextInput(
            label="Reason",
            placeholder="Why are you opening a ticket?",
            style=discord.TextStyle.long,
            required=True,
            max_length=1000,
            min_length=30,
        )
        self.add_item(self.reason)
        self.type = type

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        t = await T.insert_one(
            {
                "_id": "".join(
                    random.choices(string.ascii_letters + string.digits, k=10)
                ),
                "GuildID": interaction.guild.id,
                "UserID": interaction.user.id,
                "opened": interaction.created_at.timestamp(),
                "closed": None,
                "claimed": {"claimer": None, "claimedAt": None},
                "transcript": [],
                "type": self.type,
                "reason": self.reason.value,
            }
        )
        interaction.client.dispatch("ticket_open", t.inserted_id)
        await interaction.followup.send(
            content=f"{tick} **{interaction.user.display_name}**, your ticket has been opened!",
            ephemeral=True,
        )


async def setup(client: commands.Bot) -> None:
    await client.add_cog(Tickets(client))
