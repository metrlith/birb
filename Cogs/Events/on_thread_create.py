import discord
from discord.ext import commands
import asyncio
from utils.emojis import *
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["astro"]
forumsconfig = db["Forum Configuration"]
blacklist = db["blacklists"]
Configuration = db["Config"]

from utils.HelpEmbeds import (
    BotNotConfigured,
    Support,
)


class ForumCreaton(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        guild_id = thread.guild.id
        config_data = await forumsconfig.find_one(
            {"guild_id": guild_id, "channel_id": thread.parent_id}
        )
        if not config_data or "channel_id" not in config_data:
            return

        if thread.guild.id != guild_id:
            return
        if thread.parent_id != config_data["channel_id"]:
            return
        await asyncio.sleep(2)
        if config_data:
            from Cogs.Configuration.Components.EmbedBuilder import DisplayEmbed

            embed = await DisplayEmbed(
                config_data,
            )
            Roles = ""
            view = None
            Roled = config_data.get("role")
            if Roled:
                if not isinstance(Roled, list):
                    Roled = [Roled]

                Roles = []
                for role_id in Roled:
                    role = thread.guild.get_role(role_id)
                    if role:
                        Roles.append(role)
                Roles = ", ".join([role.mention for role in Roles])

            if config_data.get("Close") or config_data.get("Lock"):
                view = CloseLock()
                view.remove_item(view.Close)
                view.remove_item(view.lock)
                if config_data.get("Close"):
                    view.add_item(view.Close)
                if config_data.get("Lock"):
                    view.add_item(view.lock)

            msg = await thread.send(
                content=f"{Roles}",
                embed=embed,
                allowed_mentions=discord.AllowedMentions(roles=True, users=True),
                view=view,
            )
            try:
                await msg.pin()
            except discord.Forbidden:
                print("[ERROR] Unable to pin message.")
            except discord.HTTPException:
                print("[ERROR] Unable to pin message.")


class CloseLock(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @staticmethod
    async def has_staff_role(interaction: discord.Interaction, permissions=None):
        blacklists = await blacklist.find_one({"user": interaction.user.id})
        if blacklists:
            await interaction.response.send_message(
                f"{no} **{interaction.user.display_name}**, you are blacklisted from using **Astro Birb.** You are probably a shitty person and that might be why?",
                ephemeral=True,
            )
            return False

        Config = await interaction.client.config.find_one({"_id": interaction.guild.id})
        if not Config:
            await interaction.response.send_message(
                embed=BotNotConfigured(), view=Support(), ephemeral=True
            )
            return False

        if not Config.get("Permissions"):
            await interaction.response.send_message(
                f"{no} **{interaction.user.display_name}**, the permissions haven't been set up yet, please run `/config`",
                ephemeral=True,
            )
            return False

        staff_role_ids = Config["Permissions"].get("staffrole", [])
        staff_role_ids = (
            staff_role_ids if isinstance(staff_role_ids, list) else [staff_role_ids]
        )

        admin_role_ids = Config["Permissions"].get("adminrole", [])
        admin_role_ids = (
            admin_role_ids if isinstance(admin_role_ids, list) else [admin_role_ids]
        )

        if any(
            role.id in staff_role_ids + admin_role_ids
            for role in interaction.user.roles
        ):
            return True

        if interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                f"{no} **{interaction.user.display_name}**, the staff role isn't set, please run </config:1140463441136586784>!",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"{no} **{interaction.user.display_name}**, the staff role is not set up. Please tell an admin to run </config:1140463441136586784> to fix it.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            f"{no} **{interaction.user.display_name}**, you don't have permission to use this command.\n<:Arrow:1115743130461933599>**Required:** `Staff Role`",
            ephemeral=True,
        )
        return False

    @discord.ui.button(
        label="Lock",
        style=discord.ButtonStyle.blurple,
        emoji="<:close:1280576608125849731>",
    )
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_staff_role(interaction):
            return
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                f"{no} **{interaction.user.display_name},** This can only be used in a thread.",
                ephemeral=True,
            )
            return
        thread = interaction.channel
        if self.lock.label == "Lock":
            self.lock.label = "Unlock"
            self.lock.emoji = "<:unlock:1280576824065396848>"
            self.lock.style = discord.ButtonStyle.green
            await thread.edit(locked=True)
            await interaction.channel.send(
                content=f"<:close:1280576608125849731> **@{interaction.user.display_name}**, has locked the thread."
            )
        else:
            self.lock.label = "Lock"
            self.lock.emoji = "<:close:1280576608125849731>"
            self.lock.style = discord.ButtonStyle.blurple
            await interaction.channel.edit(locked=False)
            await interaction.channel.send(
                content=f"<:unlock:1280576824065396848> **@{interaction.user.display_name}**, has unlocked the thread."
            )
        await interaction.response.edit_message(view=self)

    @discord.ui.button(
        label="Close",
        style=discord.ButtonStyle.red,
        emoji="<:close:1280577170233753650>",
    )
    async def Close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self.has_staff_role(interaction):
            return
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                f"{no} **{interaction.user.display_name},** This can only be used in a thread.",
                ephemeral=True,
            )
            return
        thread = interaction.channel

        if self.Close.label == "Close":
            await thread.edit(archived=True)
            self.Close.label = "Reopen"
            self.Close.emoji = "<:Add:1163095623600447558>"

            await interaction.channel.send(
                content=f"<:close:1280577170233753650> **@{interaction.user.display_name}**, has closed the thread.",
                allowed_mentions=discord.AllowedMentions().none(),
            )

            self.Close.style = discord.ButtonStyle.green
        else:
            await interaction.channel.edit(archived=False)
            self.Close.label = "Close"
            self.Close.emoji = "<:close:1280577170233753650>"

            await interaction.channel.send(
                content=f"<:Add:1163095623600447558> **@{interaction.user.display_name}**, has reopened the thread.",
                allowed_mentions=discord.AllowedMentions().none(),
            )
            self.Close.style = discord.ButtonStyle.red

        await interaction.response.edit_message(view=self)


async def setup(client: commands.Bot) -> None:
    await client.add_cog(ForumCreaton(client))
